from __future__ import annotations

from extractor.contracts import (
    Chunk,
    ExtractionPlan,
    LensCandidate,
    RejectionReason,
    SourceSpan,
)


def candidate_rejection_reasons(
    *,
    candidate: LensCandidate,
    chunk: Chunk,
    category_fields: dict[str, frozenset[str]],
) -> list[RejectionReason]:
    reasons: list[RejectionReason] = []
    fields = category_fields.get(candidate.category)
    if fields is None:
        reasons.append(
            RejectionReason(
                code="category_not_approved",
                message=f"Category is not approved for this extraction plan: {candidate.category}",
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

    if not span_matches_chunk(candidate.source_span, chunk):
        reasons.append(
            RejectionReason(
                code="invented_span",
                message="Candidate source span does not match the chunk text at the provided offsets.",
            )
        )
    return reasons


def approved_category_fields(plan: ExtractionPlan) -> dict[str, frozenset[str]]:
    return {
        category.name: frozenset(field.name for field in category.fields)
        for category in plan.approved_categories
    }


def span_matches_chunk(source_span: SourceSpan, chunk: Chunk) -> bool:
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


__all__ = [
    "approved_category_fields",
    "candidate_rejection_reasons",
    "span_matches_chunk",
]
