from __future__ import annotations

from pydantic import ValidationError

from extractor.contracts import Chunk, ExtractionPlan, LensCandidate, RejectionReason
from extractor.source_support import (
    correction_expands_source_span,
    is_label_field,
    value_is_source_supported,
)
from extractor.critic.checks import (
    approved_category_fields,
    candidate_is_mechanically_valid,
    contains_phrase,
    qualifier_tokens,
    span_matches_chunk,
)
from extractor.critic.models import CompactCorrection


_MEANINGFUL_VALUE_QUALIFIER_PHRASES = (
    ("approximately",),
    ("approx",),
    ("about",),
    ("around",),
    ("at", "least"),
    ("at", "most"),
    ("no", "more", "than"),
    ("no", "less", "than"),
    ("more", "than"),
    ("less", "than"),
    ("up",),
    ("down",),
    ("subject", "to"),
)


def materialize_correction(
    *,
    raw: CompactCorrection | None,
    original: LensCandidate,
    chunk: Chunk,
) -> tuple[LensCandidate | None, list[RejectionReason]]:
    """Merge a compact correction delta into a strict LensCandidate.

    Identity and provenance fields come from the original candidate, never from
    the LLM. Bytes and end_char are derived from the selected chunk text.
    """
    if raw is None:
        return None, [
            RejectionReason(
                code="schema_violation",
                message="Corrected critic verdict must include a correction payload.",
            )
        ]

    span_start_char = (
        raw.span_start_char
        if raw.span_start_char is not None
        else original.source_span.start_char
    )
    span_text = raw.span_text if raw.span_text is not None else original.source_span.text

    relative_start = span_start_char - chunk.start_char
    relative_end = relative_start + len(span_text)
    if (
        relative_start < 0
        or relative_end > len(chunk.text)
        or chunk.text[relative_start:relative_end] != span_text
    ):
        return None, [
            RejectionReason(
                code="invented_span",
                message=(
                    "Corrected candidate span_text does not match the chunk "
                    f"slice at start_char {span_start_char}."
                ),
            )
        ]

    end_char = span_start_char + len(span_text)
    prefix_bytes = len(chunk.text[:relative_start].encode("utf-8"))
    text_bytes = len(span_text.encode("utf-8"))
    start_byte = chunk.start_byte + prefix_bytes
    end_byte = start_byte + text_bytes

    candidate_dict = original.model_dump()
    if raw.value is not None:
        candidate_dict["value"] = raw.value
    if raw.category is not None:
        candidate_dict["category"] = raw.category
    if raw.field_name is not None:
        candidate_dict["field_name"] = raw.field_name
    candidate_dict["source_span"] = {
        "doc_id": original.doc_id,
        "chunk_id": original.chunk_id,
        "start_char": span_start_char,
        "end_char": end_char,
        "start_byte": start_byte,
        "end_byte": end_byte,
        "text": span_text,
    }
    try:
        return LensCandidate.model_validate(candidate_dict), []
    except ValidationError as exc:
        message = "; ".join(
            f"{'.'.join(str(p) for p in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ) or "Corrected candidate failed contract validation."
        return None, [
            RejectionReason(
                code="invented_span",
                message=f"Corrected candidate violated invariants: {message}",
            )
        ]


def correction_rejection_reasons(
    *,
    plan: ExtractionPlan,
    chunk: Chunk,
    original: LensCandidate,
    corrected: LensCandidate | None,
) -> list[RejectionReason]:
    if corrected is None:
        return []

    reasons: list[RejectionReason] = []
    if corrected.candidate_id != original.candidate_id:
        reasons.append(
            RejectionReason(
                code="schema_violation",
                message="Corrected candidate must preserve candidate_id.",
            )
        )
    if corrected.run_id != original.run_id:
        reasons.append(
            RejectionReason(
                code="schema_violation",
                message="Corrected candidate must preserve run_id.",
            )
        )
    if corrected.doc_id != original.doc_id:
        reasons.append(
            RejectionReason(
                code="schema_violation",
                message="Corrected candidate must preserve doc_id.",
            )
        )
    if corrected.chunk_id != original.chunk_id:
        reasons.append(
            RejectionReason(
                code="schema_violation",
                message="Corrected candidate must preserve chunk_id.",
            )
        )
    if corrected.lens != original.lens:
        reasons.append(
            RejectionReason(
                code="schema_violation",
                message="Corrected candidate must preserve lens.",
            )
        )
    if corrected.executor_call_id != original.executor_call_id:
        reasons.append(
            RejectionReason(
                code="schema_violation",
                message="Corrected candidate must preserve executor_call_id.",
            )
        )

    fields = approved_category_fields(plan).get(corrected.category)
    if fields is None or corrected.field_name not in fields:
        reasons.append(
            RejectionReason(
                code="schema_violation",
                message="Corrected candidate category and field must be approved by the plan.",
            )
        )
    if not span_matches_chunk(corrected.source_span, chunk):
        reasons.append(
            RejectionReason(
                code="invented_span",
                message="Corrected candidate source span must match the chunk text at its offsets.",
            )
        )
    if correction_expands_source_span(original=original, corrected=corrected):
        reasons.append(
            RejectionReason(
                code="schema_violation",
                message=(
                    "Corrected candidate source span may narrow the executor "
                    "span but must not expand beyond it."
                ),
            )
        )
    if not is_label_field(corrected.field_name) and not value_is_source_supported(
        corrected
    ):
        reasons.append(
            RejectionReason(
                code="invented_span",
                message=(
                    "Corrected candidate value adds words or units that are not "
                    "grounded in the corrected source span."
                ),
            )
        )
    lost_qualifier = _lost_source_qualifier(original=original, corrected=corrected)
    if lost_qualifier is not None:
        reasons.append(
            RejectionReason(
                code="schema_violation",
                message=(
                    "Corrected candidate value drops source qualifier "
                    f"{lost_qualifier!r} while keeping it in the source span."
                ),
            )
        )
    return reasons


def should_preserve_original_for_correction(
    *,
    plan: ExtractionPlan,
    chunk: Chunk,
    original: LensCandidate,
    corrected: LensCandidate | None,
    reasons: list[RejectionReason],
) -> bool:
    if not candidate_is_mechanically_valid(
        plan=plan,
        chunk=chunk,
        candidate=original,
    ):
        return False
    if corrected is not None:
        # Field identity is part of the executor/schema contract once the
        # original is mechanically valid; critic can reject, but not relabel it.
        return _correction_changes_schema_slot(original, corrected) or (
            _only_expanded_span_rejection(reasons)
        )
    return _only_structural_materialization_rejections(reasons)


def _correction_changes_schema_slot(
    original: LensCandidate,
    corrected: LensCandidate,
) -> bool:
    return (
        corrected.category != original.category
        or corrected.field_name != original.field_name
    )


def _only_expanded_span_rejection(reasons: list[RejectionReason]) -> bool:
    return len(reasons) == 1 and "must not expand beyond it" in reasons[0].message


def _only_structural_materialization_rejections(
    reasons: list[RejectionReason],
) -> bool:
    if not reasons:
        return False
    return all(_is_structural_materialization_rejection(reason) for reason in reasons)


def _is_structural_materialization_rejection(reason: RejectionReason) -> bool:
    return reason.code == "invented_span" and (
        reason.message.startswith("Corrected candidate span_text does not match")
        or reason.message.startswith("Corrected candidate violated invariants")
    )


def _lost_source_qualifier(
    *,
    original: LensCandidate,
    corrected: LensCandidate,
) -> str | None:
    if corrected.value == original.value:
        return None

    span_tokens = qualifier_tokens(corrected.source_span.text)
    value_tokens = qualifier_tokens(corrected.value)
    for phrase in _MEANINGFUL_VALUE_QUALIFIER_PHRASES:
        if contains_phrase(span_tokens, phrase) and not contains_phrase(
            value_tokens,
            phrase,
        ):
            return " ".join(phrase)
    return None


__all__ = [
    "correction_rejection_reasons",
    "materialize_correction",
    "should_preserve_original_for_correction",
]
