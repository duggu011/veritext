from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from extractor.audit import CandidateRejection
from extractor.contracts import (
    Chunk,
    CriticReport,
    ExtractionPlan,
    LensCandidate,
    RejectionReason,
    VerifierReport,
)


NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]
Confidence = Annotated[float, Field(strict=True, ge=0.0, le=1.0)]


class VerifierModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class VerifierStageInput(VerifierModel):
    run_id: NonEmptyStr
    plan: ExtractionPlan
    candidate: LensCandidate
    critic_report: CriticReport
    chunk: Chunk


class VerifierReviewPayload(VerifierModel):
    span_verified: bool = Field(strict=True)
    category_verified: bool = Field(strict=True)
    alignment_score: Confidence
    accepted: bool = Field(strict=True)
    rejection_reasons: tuple[RejectionReason, ...]


class VerifierTaskResult(VerifierModel):
    accepted_candidates: tuple[LensCandidate, ...]
    rejected_candidates: tuple[LensCandidate, ...]
    reports: tuple[VerifierReport, ...]
    rejections: tuple[CandidateRejection, ...]


class VerificationResult(VerifierTaskResult):
    pass


__all__ = [
    "VerificationResult",
    "VerifierReviewPayload",
    "VerifierStageInput",
    "VerifierTaskResult",
]
