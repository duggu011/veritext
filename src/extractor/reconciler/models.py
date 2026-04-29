from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from extractor.audit import CandidateRejection
from extractor.contracts import (
    CriticReport,
    DataPoint,
    ExtractionPlan,
    LensCandidate,
    RejectionReason,
    VerifierReport,
)


NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]
Confidence = Annotated[float, Field(strict=True, ge=0.0, le=1.0)]


class ReconcilerModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReconcilerStageInput(ReconcilerModel):
    run_id: NonEmptyStr
    plan: ExtractionPlan
    candidates: tuple[LensCandidate, ...] = Field(min_length=1)
    critic_reports: tuple[CriticReport, ...] = Field(min_length=1)
    verifier_reports: tuple[VerifierReport, ...] = Field(min_length=1)


class ReconciledDataPointPayload(ReconcilerModel):
    category: NonEmptyStr
    field_name: NonEmptyStr
    value: NonEmptyStr
    source_candidate_id: NonEmptyStr
    contributing_candidate_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    confidence: Confidence

    @model_validator(mode="after")
    def validate_source_contributes(self) -> ReconciledDataPointPayload:
        if self.source_candidate_id not in self.contributing_candidate_ids:
            raise ValueError("source_candidate_id must be one of contributing_candidate_ids")
        if len(self.contributing_candidate_ids) != len(set(self.contributing_candidate_ids)):
            raise ValueError("contributing_candidate_ids must be unique")
        return self


class RejectedCandidatePayload(ReconcilerModel):
    candidate_id: NonEmptyStr
    reasons: tuple[RejectionReason, ...] = Field(min_length=1)


class ReconciliationBatch(ReconcilerModel):
    data_points: tuple[ReconciledDataPointPayload, ...]
    rejected_candidates: tuple[RejectedCandidatePayload, ...]


class ReconciliationResult(ReconcilerModel):
    data_points: tuple[DataPoint, ...]
    rejections: tuple[CandidateRejection, ...]


__all__ = [
    "ReconciledDataPointPayload",
    "ReconciliationBatch",
    "ReconciliationResult",
    "ReconcilerStageInput",
    "RejectedCandidatePayload",
]
