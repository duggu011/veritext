from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from extractor.audit import CandidateRejection
from extractor.contracts import CriticReport, LensCandidate
from extractor.contracts.models import RejectionReasonCode
from extractor.llm.views import LLMChunkView, LLMCandidateView, LLMSchemaCard


NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
Evidence = Annotated[str, Field(strict=True, min_length=1, max_length=200)]


class CriticModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CompactCorrection(CriticModel):
    # All fields are deltas over the original candidate identified by `id`.
    # Identity/provenance fields stay server-side and are never accepted from
    # the model at this boundary.
    value: NonEmptyStr | None = None
    category: NonEmptyStr | None = None
    field_name: NonEmptyStr | None = None
    source_start_char: NonNegativeInt | None = None
    source_text: Annotated[str, Field(strict=True, min_length=1)] | None = None


class CriticBatchStageInput(CriticModel):
    schema_card: LLMSchemaCard
    chunk_view: LLMChunkView
    candidates: tuple[LLMCandidateView, ...]


class CriticVerdict(CriticModel):
    id: NonEmptyStr
    decision: Literal["accept", "reject", "correct"]
    code: RejectionReasonCode | None = None
    evidence: Evidence | None = None
    correction: CompactCorrection | None = None

    @model_validator(mode="after")
    def validate_decision_fields(self) -> CriticVerdict:
        if self.decision == "accept" and self.code is not None:
            raise ValueError("accepted critic verdicts must not include code")
        if self.decision != "accept" and self.code is None:
            raise ValueError("non-accepted critic verdicts must include code")
        if self.decision == "correct" and self.correction is None:
            raise ValueError("corrected critic verdicts must include correction")
        if self.decision != "correct" and self.correction is not None:
            raise ValueError("only corrected critic verdicts may include correction")
        return self


class CriticBatchVerdicts(CriticModel):
    verdicts: tuple[CriticVerdict, ...]


class CriticTaskResult(CriticModel):
    accepted_candidates: tuple[LensCandidate, ...]
    rejected_candidates: tuple[LensCandidate, ...]
    reports: tuple[CriticReport, ...]
    rejections: tuple[CandidateRejection, ...]


class CriticResult(CriticTaskResult):
    pass


__all__ = [
    "CriticBatchVerdicts",
    "CriticBatchStageInput",
    "CriticVerdict",
    "CriticResult",
    "CriticTaskResult",
    "CompactCorrection",
]
