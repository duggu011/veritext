from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from extractor.audit import CandidateRejection
from extractor.contracts import Chunk, CriticIssue, CriticReport, ExtractionPlan, LensCandidate
from extractor.contracts.models import LensName


NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]
Confidence = Annotated[float, Field(strict=True, ge=0.0, le=1.0)]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]


class CriticModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# Relaxed mirror of SourceSpan/LensCandidate for the critic tool input only.
# The critic returns char offset + exact text; the service derives end_char and
# byte offsets from the chunk before re-validating against the strict contracts.
# This both spares the LLM unreliable byte arithmetic and lets a malformed
# correction surface as a typed rejection rather than crashing the run.
class RawSourceSpan(CriticModel):
    doc_id: NonEmptyStr
    chunk_id: NonEmptyStr
    start_char: NonNegativeInt
    text: Annotated[str, Field(strict=True, min_length=1)]


class RawCorrectedCandidate(CriticModel):
    candidate_id: NonEmptyStr
    run_id: NonEmptyStr
    doc_id: NonEmptyStr
    chunk_id: NonEmptyStr
    lens: LensName
    category: NonEmptyStr
    field_name: NonEmptyStr
    value: NonEmptyStr
    source_span: RawSourceSpan
    confidence: Confidence
    executor_call_id: NonEmptyStr


class CriticBatchStageInput(CriticModel):
    run_id: NonEmptyStr
    plan: ExtractionPlan
    chunk: Chunk
    candidates: tuple[LensCandidate, ...]


class CriticBatchReportPayload(CriticModel):
    candidate_id: NonEmptyStr
    plausibility_score: Confidence
    accepted: bool = Field(strict=True)
    issues: tuple[CriticIssue, ...]
    corrected_candidate: RawCorrectedCandidate | None = None

    @model_validator(mode="after")
    def validate_rejection_issues(self) -> CriticBatchReportPayload:
        if not self.accepted and not self.issues:
            raise ValueError("rejected critic payloads must include at least one issue")
        return self


class CriticBatchReviewPayload(CriticModel):
    reports: tuple[CriticBatchReportPayload, ...]


class CriticTaskResult(CriticModel):
    accepted_candidates: tuple[LensCandidate, ...]
    rejected_candidates: tuple[LensCandidate, ...]
    reports: tuple[CriticReport, ...]
    rejections: tuple[CandidateRejection, ...]


class CriticResult(CriticTaskResult):
    pass


__all__ = [
    "CriticBatchReportPayload",
    "CriticBatchReviewPayload",
    "CriticBatchStageInput",
    "CriticResult",
    "CriticTaskResult",
    "RawCorrectedCandidate",
    "RawSourceSpan",
]
