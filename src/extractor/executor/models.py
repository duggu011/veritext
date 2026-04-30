from __future__ import annotations

from typing import Annotated

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from extractor.audit import CandidateRejection
from extractor.contracts import LensCandidate
from extractor.contracts.models import LensName
from extractor.llm.views import LLMChunkView, LLMSchemaCard


NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]


class ExecutorModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExecutorStageInput(ExecutorModel):
    schema_card: LLMSchemaCard
    lens: LensName
    chunk_view: LLMChunkView


class ExtractedCandidatePayload(ExecutorModel):
    # The model returns char offset + source length only. The service reconstructs
    # source text, end_char, and UTF-8 byte offsets from the chunk text.
    category: NonEmptyStr
    field_name: NonEmptyStr
    value: NonEmptyStr
    source_length: NonNegativeInt
    # Kimi has been observed returning start_text as a typo for this integer
    # field. Keep the emitted schema strict as start_char, but accept the typo at
    # validation time so exact-span checks can still accept or reject the value.
    start_char: NonNegativeInt = Field(
        validation_alias=AliasChoices("start_char", "start_text")
    )
    confidence: Confidence


class ExecutorCandidateBatch(ExecutorModel):
    candidates: tuple[ExtractedCandidatePayload, ...]


class ExecutorTaskResult(ExecutorModel):
    accepted_candidates: tuple[LensCandidate, ...]
    rejected_candidates: tuple[LensCandidate, ...]
    rejections: tuple[CandidateRejection, ...]


class ExecutionResult(ExecutorTaskResult):
    pass


__all__ = [
    "ExecutionResult",
    "ExecutorCandidateBatch",
    "ExecutorStageInput",
    "ExecutorTaskResult",
    "ExtractedCandidatePayload",
]
