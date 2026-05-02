from __future__ import annotations

import re

from extractor.contracts import (
    Chunk,
    ExtractionPlan,
    FieldDefinition,
    LensCandidate,
    RejectionReason,
    SourceSpan,
)
from extractor.llm.views import short_candidate_id
from extractor.source_support import value_is_source_supported
from extractor.critic.models import CriticVerdict


_ATOMIC_FIELD_ROLE_TOKENS = frozenset(
    {
        "amount",
        "count",
        "date",
        "deadline",
        "duration",
        "number",
        "pct",
        "percent",
        "percentage",
        "period",
        "quantity",
        "rate",
        "ratio",
        "term",
        "time",
        "total",
        "value",
        "year",
    }
)
_CONTEXT_OBJECTION_TOKENS = frozenset(
    {"alone", "ambiguous", "anchor", "anchored", "context", "specific", "vague"}
)
_COMPANION_OBJECTION_TOKENS = frozenset(
    {"category", "companion", "entry", "field", "record", "without"}
)


def contradicted_rejection_reasons(
    *,
    plan: ExtractionPlan,
    chunk: Chunk,
    candidate: LensCandidate,
    verdict: CriticVerdict,
) -> list[RejectionReason]:
    if verdict.code is None:
        return []

    reasons: list[RejectionReason] = []
    fields = approved_category_fields(plan).get(candidate.category)
    schema_approved = fields is not None and candidate.field_name in fields
    span_matches = span_matches_chunk(candidate.source_span, chunk)

    if verdict.code == "category_not_approved" and schema_approved:
        reasons.append(
            RejectionReason(
                code="category_not_approved",
                message=(
                    "Candidate category and field are present in the approved "
                    "schema; category_not_approved is mechanically false."
                ),
            )
        )
    if verdict.code == "invalid_source_offsets" and span_matches:
        reasons.append(
            RejectionReason(
                code="invalid_source_offsets",
                message=(
                    "Candidate source offsets and span_text exactly match the "
                    "chunk; invalid_source_offsets is mechanically false."
                ),
            )
        )
    if verdict.code in {"critic_rejected", "schema_violation", "invented_span"} and (
        _is_source_backed_corporate_event_asset_detail(
            plan=plan,
            chunk=chunk,
            candidate=candidate,
        )
    ):
        reasons.append(
            RejectionReason(
                code=verdict.code,
                message=(
                    "CorporateEvent.asset_detail is approved for source-backed "
                    "asset details, and this candidate is mechanically valid "
                    "under that schema role."
                ),
            )
        )
    if verdict.code in {"critic_rejected", "schema_violation"} and (
        _is_context_only_atomic_field_rejection(
            plan=plan,
            chunk=chunk,
            candidate=candidate,
            verdict=verdict,
        )
    ):
        reasons.append(
            RejectionReason(
                code=verdict.code,
                message=(
                    "Candidate field is an approved atomic source-backed role; "
                    "companion-field context is reconstructed after candidate "
                    "review."
                ),
            )
        )
    return reasons


def candidate_is_mechanically_valid(
    *,
    plan: ExtractionPlan,
    chunk: Chunk,
    candidate: LensCandidate,
) -> bool:
    fields = approved_category_fields(plan).get(candidate.category)
    return (
        fields is not None
        and candidate.field_name in fields
        and span_matches_chunk(candidate.source_span, chunk)
        and value_is_source_supported(candidate)
    )


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


def approved_category_fields(plan: ExtractionPlan) -> dict[str, frozenset[str]]:
    return {
        category.name: frozenset(field.name for field in category.fields)
        for category in plan.approved_categories
    }


def qualifier_tokens(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", text.casefold()))


def contains_phrase(tokens: tuple[str, ...], phrase: tuple[str, ...]) -> bool:
    if len(phrase) > len(tokens):
        return False
    return any(
        tokens[index : index + len(phrase)] == phrase
        for index in range(len(tokens) - len(phrase) + 1)
    )


def _is_context_only_atomic_field_rejection(
    *,
    plan: ExtractionPlan,
    chunk: Chunk,
    candidate: LensCandidate,
    verdict: CriticVerdict,
) -> bool:
    return (
        candidate_is_mechanically_valid(plan=plan, chunk=chunk, candidate=candidate)
        and _is_atomic_field_role(plan=plan, candidate=candidate)
        and _is_companion_context_objection(verdict.evidence)
    )


def _is_atomic_field_role(
    *,
    plan: ExtractionPlan,
    candidate: LensCandidate,
) -> bool:
    field = _approved_field_definition(plan=plan, candidate=candidate)
    if field is None:
        return False
    return bool(_field_role_tokens(field.name) & _ATOMIC_FIELD_ROLE_TOKENS)


def _approved_field_definition(
    *,
    plan: ExtractionPlan,
    candidate: LensCandidate,
) -> FieldDefinition | None:
    for category in plan.approved_categories:
        if category.name != candidate.category:
            continue
        for field in category.fields:
            if field.name == candidate.field_name:
                return field
    return None


def _field_role_tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.casefold().replace("_", " ")))


def _is_companion_context_objection(evidence: str | None) -> bool:
    if not evidence:
        return False
    tokens = set(qualifier_tokens(evidence))
    return bool(tokens & _CONTEXT_OBJECTION_TOKENS) and bool(
        tokens & _COMPANION_OBJECTION_TOKENS
    )


def _is_source_backed_corporate_event_asset_detail(
    *,
    plan: ExtractionPlan,
    chunk: Chunk,
    candidate: LensCandidate,
) -> bool:
    if candidate.category != "CorporateEvent" or candidate.field_name != "asset_detail":
        return False
    if not candidate_is_mechanically_valid(
        plan=plan,
        chunk=chunk,
        candidate=candidate,
    ):
        return False
    return _asset_detail_description_allows_source_backed_details(plan)


def _asset_detail_description_allows_source_backed_details(
    plan: ExtractionPlan,
) -> bool:
    for category in plan.approved_categories:
        if category.name != "CorporateEvent":
            continue
        for field in category.fields:
            if field.name != "asset_detail":
                continue
            description = f"{category.description} {field.description}".casefold()
            detail_role = any(
                term in description
                for term in ("detail", "description", "attribute", "profile")
            )
            source_role = any(
                term in description
                for term in ("source-backed", "source-stated", "stated", "verbatim")
            )
            return detail_role and source_role
    return False


__all__ = [
    "approved_category_fields",
    "candidate_is_mechanically_valid",
    "contains_phrase",
    "contradicted_rejection_reasons",
    "qualifier_tokens",
    "span_matches_chunk",
]
