from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from extractor.audit import CandidateRejection
from extractor.contracts import (
    LensCandidate,
    VerifierReport,
)
from extractor.contracts.models import RejectionReasonCode
from extractor.llm.views import LLMChunkView, LLMCandidateView, LLMSchemaCard


NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]
Evidence = Annotated[str, Field(strict=True, min_length=1, max_length=200)]


class VerifierModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CriticSummary(VerifierModel):
    accepted: bool = Field(strict=True)


class VerifierBatchItem(VerifierModel):
    candidate: LLMCandidateView
    critic_summary: CriticSummary


class VerifierBatchStageInput(VerifierModel):
    schema_card: LLMSchemaCard
    chunk_view: LLMChunkView
    items: tuple[VerifierBatchItem, ...]


class VerifierVerdict(VerifierModel):
    id: NonEmptyStr
    decision: Literal["accept", "reject"]
    code: RejectionReasonCode | None = None
    evidence: Evidence | None = None

    @model_validator(mode="after")
    def validate_decision_fields(self) -> VerifierVerdict:
        if self.decision == "accept" and self.code is not None:
            raise ValueError("accepted verifier verdicts must not include code")
        if self.decision == "reject" and self.code is None:
            raise ValueError("rejected verifier verdicts must include code")
        return self


class VerifierBatchVerdicts(VerifierModel):
    verdicts: tuple[VerifierVerdict, ...]


class VerifierTaskResult(VerifierModel):
    accepted_candidates: tuple[LensCandidate, ...]
    rejected_candidates: tuple[LensCandidate, ...]
    reports: tuple[VerifierReport, ...]
    rejections: tuple[CandidateRejection, ...]


class VerificationResult(VerifierTaskResult):
    pass


__all__ = [
    "CriticSummary",
    "VerificationResult",
    "VerifierBatchItem",
    "VerifierBatchVerdicts",
    "VerifierBatchStageInput",
    "VerifierTaskResult",
    "VerifierVerdict",
]
