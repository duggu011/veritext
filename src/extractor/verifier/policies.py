from __future__ import annotations

import hashlib

from extractor.contracts import (
    Chunk,
    ExtractionPlan,
    LensCandidate,
    RejectionReason,
    SourceSpan,
    VerifierReport,
)
from extractor.contracts.models import RejectionReasonCode
from extractor.source_support import is_label_field, value_is_source_supported
from extractor.verifier.errors import VerifierError
from extractor.verifier.models import VerifierVerdict


_SPAN_CORRECTNESS_CODES: frozenset[RejectionReasonCode] = frozenset(
    {"invented_span", "invalid_source_offsets", "ambiguous_source_span"}
)


def build_verifier_report(
    *,
    plan: ExtractionPlan,
    chunk: Chunk,
    candidate: LensCandidate,
    verdict: VerifierVerdict,
    verifier_call_id: str,
) -> VerifierReport:
    deterministic_reasons = _deterministic_rejection_reasons(
        plan=plan,
        chunk=chunk,
        candidate=candidate,
    )
    span_matches = _span_matches_chunk(candidate.source_span, chunk)
    schema_approved = _candidate_schema_approved(plan=plan, candidate=candidate)
    value_supported = value_is_source_supported(candidate)
    llm_reasons = _llm_rejection_reasons(verdict)
    if span_matches or schema_approved or value_supported:
        # Deterministic checks are authoritative for mechanical schema, offsets,
        # exact span text, and source support. Drop LLM objections
        # that contradict those checks; keep any remaining reasons.
        llm_reasons = tuple(
            reason
            for reason in llm_reasons
            if not _is_contradicted_llm_reason(
                reason=reason,
                span_matches=span_matches,
                schema_approved=schema_approved,
                value_supported=value_supported,
            )
        )
    rejection_reasons = _merged_rejection_reasons(
        (*llm_reasons, *deterministic_reasons)
    )
    span_verified = not any(
        reason.code in _SPAN_CORRECTNESS_CODES for reason in rejection_reasons
    )
    category_verified = not any(
        reason.code in {"category_not_approved", "schema_violation"}
        for reason in rejection_reasons
    )
    accepted = not rejection_reasons
    alignment_score = 1.0 if accepted else 0.0

    return VerifierReport(
        report_id=_stable_report_id(
            candidate=candidate,
            verifier_call_id=verifier_call_id,
            span_verified=span_verified,
            category_verified=category_verified,
            alignment_score=alignment_score,
            accepted=accepted,
            rejection_reasons=rejection_reasons,
        ),
        run_id=plan.run_id,
        candidate_id=candidate.candidate_id,
        verifier_call_id=verifier_call_id,
        span_verified=span_verified,
        category_verified=category_verified,
        alignment_score=alignment_score,
        accepted=accepted,
        rejection_reasons=() if accepted else rejection_reasons,
    )


def stable_missing_report_id(
    *,
    candidate: LensCandidate,
    verifier_call_id: str,
    reasons: tuple[RejectionReason, ...],
) -> str:
    reason_identity = "|".join(f"{reason.code}:{reason.message}" for reason in reasons)
    identity = f"{candidate.candidate_id}|{verifier_call_id}|missing|{reason_identity}"
    return f"verifier-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


def stable_rejection_id(candidate: LensCandidate, report: VerifierReport) -> str:
    reason_identity = "|".join(
        f"{reason.code}:{reason.message}" for reason in report.rejection_reasons
    )
    identity = f"{candidate.candidate_id}|{report.report_id}|{reason_identity}"
    return f"rejection-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


def _deterministic_rejection_reasons(
    *,
    plan: ExtractionPlan,
    chunk: Chunk,
    candidate: LensCandidate,
) -> tuple[RejectionReason, ...]:
    reasons: list[RejectionReason] = []
    fields = _approved_category_fields(plan).get(candidate.category)
    if fields is None:
        reasons.append(
            RejectionReason(
                code="category_not_approved",
                message=(
                    "Category is not approved for this extraction plan: "
                    f"{candidate.category}"
                ),
            )
        )
    elif candidate.field_name not in fields:
        reasons.append(
            RejectionReason(
                code="schema_violation",
                message=(
                    f"Field {candidate.field_name} is not approved for category "
                    f"{candidate.category}"
                ),
            )
        )

    if not _span_matches_chunk(candidate.source_span, chunk):
        reasons.append(
            RejectionReason(
                code="invented_span",
                message=(
                    "Candidate source span does not match the chunk text at the "
                    "provided offsets."
                ),
            )
        )
    elif not is_label_field(candidate.field_name) and not value_is_source_supported(
        candidate
    ):
        reasons.append(
            RejectionReason(
                code="invented_span",
                message=(
                    "Candidate value adds words or units that are not grounded "
                    "in the selected source span."
                ),
            )
        )
    return tuple(reasons)


def _candidate_schema_approved(
    *,
    plan: ExtractionPlan,
    candidate: LensCandidate,
) -> bool:
    fields = _approved_category_fields(plan).get(candidate.category)
    return fields is not None and candidate.field_name in fields


def _is_contradicted_llm_reason(
    *,
    reason: RejectionReason,
    span_matches: bool,
    schema_approved: bool,
    value_supported: bool,
) -> bool:
    if reason.code in {"invalid_source_offsets", "ambiguous_source_span"}:
        return span_matches
    if reason.code == "invented_span":
        return span_matches and value_supported
    if reason.code == "category_not_approved":
        return schema_approved
    if reason.code == "schema_violation":
        return schema_approved and span_matches and value_supported
    return False


def _llm_rejection_reasons(verdict: VerifierVerdict) -> tuple[RejectionReason, ...]:
    if verdict.decision == "accept":
        return ()
    code = _required_code(verdict)
    return (
        RejectionReason(
            code=code,
            message=verdict.evidence or _default_message(code),
        ),
    )


def _required_code(verdict: VerifierVerdict) -> RejectionReasonCode:
    if verdict.code is None:
        raise VerifierError("rejected verifier verdict must include a rejection code")
    return verdict.code


def _default_message(code: RejectionReasonCode) -> str:
    messages = {
        "invalid_source_offsets": (
            "Candidate source offsets are not valid for the source chunk."
        ),
        "invented_span": "Candidate value is not grounded in the selected source span.",
        "category_not_approved": (
            "Candidate category is not approved by the extraction schema."
        ),
        "critic_rejected": "Critic rejected the candidate.",
        "verifier_rejected": "Verifier rejected the candidate.",
        "reconciler_rejected": "Reconciler rejected the candidate.",
        "schema_violation": (
            "Candidate category or field does not match the approved schema."
        ),
        "ambiguous_source_span": (
            "Candidate source span is ambiguous within the source chunk."
        ),
        "duplicate_candidate": (
            "Candidate duplicates another candidate selected for review."
        ),
    }
    return messages[code]


def _merged_rejection_reasons(
    reasons: tuple[RejectionReason, ...],
) -> tuple[RejectionReason, ...]:
    merged: list[RejectionReason] = []
    seen: set[tuple[str, str]] = set()
    for reason in reasons:
        key = (reason.code, reason.message)
        if key not in seen:
            merged.append(reason)
            seen.add(key)
    return tuple(merged)


def _span_matches_chunk(source_span: SourceSpan, chunk: Chunk) -> bool:
    if source_span.start_char < chunk.start_char or source_span.end_char > chunk.end_char:
        return False
    if source_span.start_byte < chunk.start_byte or source_span.end_byte > chunk.end_byte:
        return False

    relative_start_char = source_span.start_char - chunk.start_char
    relative_end_char = source_span.end_char - chunk.start_char
    relative_start_byte = source_span.start_byte - chunk.start_byte
    relative_end_byte = source_span.end_byte - chunk.start_byte
    chunk_bytes = chunk.text.encode("utf-8")
    return (
        chunk.text[relative_start_char:relative_end_char] == source_span.text
        and chunk_bytes[relative_start_byte:relative_end_byte]
        == source_span.text.encode("utf-8")
    )


def _approved_category_fields(plan: ExtractionPlan) -> dict[str, frozenset[str]]:
    return {
        category.name: frozenset(field.name for field in category.fields)
        for category in plan.approved_categories
    }


def _stable_report_id(
    *,
    candidate: LensCandidate,
    verifier_call_id: str,
    span_verified: bool,
    category_verified: bool,
    alignment_score: float,
    accepted: bool,
    rejection_reasons: tuple[RejectionReason, ...],
) -> str:
    reason_identity = "|".join(
        f"{reason.code}:{reason.message}" for reason in rejection_reasons
    )
    identity = "|".join(
        (
            candidate.candidate_id,
            verifier_call_id,
            str(span_verified),
            str(category_verified),
            str(alignment_score),
            str(accepted),
            reason_identity,
        )
    )
    return f"verifier-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


__all__ = [
    "build_verifier_report",
    "stable_missing_report_id",
    "stable_rejection_id",
]
