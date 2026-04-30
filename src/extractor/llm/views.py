from __future__ import annotations

import hashlib

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from extractor.contracts import Chunk, ExtractionPlan, LensCandidate
from extractor.contracts.models import LensName


NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]
Confidence = Annotated[float, Field(strict=True, ge=0.0, le=1.0)]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
_HEX = set("0123456789abcdef")


class LLMViewModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LLMFieldCard(LLMViewModel):
    name: NonEmptyStr
    value_type: NonEmptyStr
    description: NonEmptyStr


class LLMCategoryCard(LLMViewModel):
    name: NonEmptyStr
    description: NonEmptyStr
    fields: tuple[LLMFieldCard, ...] = Field(min_length=1)


class LLMSchemaCard(LLMViewModel):
    categories: tuple[LLMCategoryCard, ...] = Field(min_length=1)
    enabled_lenses: tuple[LensName, ...] = Field(min_length=1)


class LLMChunkView(LLMViewModel):
    start_char: NonNegativeInt
    text: Annotated[str, Field(strict=True, min_length=1)]


class LLMCandidateView(LLMViewModel):
    id: NonEmptyStr
    lens: LensName
    category: NonEmptyStr
    field_name: NonEmptyStr
    value: NonEmptyStr
    span_start_char: NonNegativeInt
    span_text: NonEmptyStr
    confidence: Confidence


def schema_card_from_plan(plan: ExtractionPlan) -> LLMSchemaCard:
    return LLMSchemaCard(
        categories=tuple(
            LLMCategoryCard(
                name=category.name,
                description=category.description,
                fields=tuple(
                    LLMFieldCard(
                        name=field.name,
                        value_type=field.value_type,
                        description=field.description,
                    )
                    for field in category.fields
                ),
            )
            for category in plan.approved_categories
        ),
        enabled_lenses=plan.enabled_lenses,
    )


def chunk_view_from_chunk(chunk: Chunk) -> LLMChunkView:
    return LLMChunkView(start_char=chunk.start_char, text=chunk.text)


def short_candidate_id(candidate_id: str) -> str:
    token_source = candidate_id.removeprefix("candidate-").lower()
    if len(token_source) >= 12 and all(char in _HEX for char in token_source[:12]):
        return token_source[:12]
    return hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:12]


def candidate_view_from_candidate(candidate: LensCandidate) -> LLMCandidateView:
    return LLMCandidateView(
        id=short_candidate_id(candidate.candidate_id),
        lens=candidate.lens,
        category=candidate.category,
        field_name=candidate.field_name,
        value=candidate.value,
        span_start_char=candidate.source_span.start_char,
        span_text=candidate.source_span.text,
        confidence=candidate.confidence,
    )


def build_candidate_view_map(
    candidates: tuple[LensCandidate, ...],
) -> tuple[tuple[LLMCandidateView, ...], dict[str, LensCandidate]]:
    views: list[LLMCandidateView] = []
    candidates_by_view_id: dict[str, LensCandidate] = {}
    for candidate in candidates:
        view = candidate_view_from_candidate(candidate)
        existing = candidates_by_view_id.get(view.id)
        if existing is not None and existing.candidate_id != candidate.candidate_id:
            raise ValueError(
                "candidate short ID collision between "
                f"{existing.candidate_id} and {candidate.candidate_id}"
            )
        views.append(view)
        candidates_by_view_id[view.id] = candidate
    return tuple(views), candidates_by_view_id


__all__ = [
    "LLMCategoryCard",
    "LLMChunkView",
    "LLMCandidateView",
    "LLMFieldCard",
    "LLMSchemaCard",
    "build_candidate_view_map",
    "candidate_view_from_candidate",
    "chunk_view_from_chunk",
    "schema_card_from_plan",
    "short_candidate_id",
]
