from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from extractor.audit import CandidateRejection
from extractor.contracts import CriticReport, LensCandidate
from extractor.contracts.models import RejectionReasonCode
from extractor.llm.payloads import normalize_verdict_payload, parse_json_if_string
from extractor.llm.views import LLMChunkView, LLMCandidateView, LLMSchemaCard


NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
EVIDENCE_MAX_CHARS = 200
Evidence = Annotated[str, Field(strict=True, min_length=1, max_length=EVIDENCE_MAX_CHARS)]


class CriticModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CompactCorrection(CriticModel):
    # All fields are deltas over the original candidate identified by `id`.
    # Identity/provenance fields stay server-side and are never accepted from
    # the model at this boundary.
    value: NonEmptyStr | None = None
    category: NonEmptyStr | None = None
    field_name: NonEmptyStr | None = None
    span_start_char: NonNegativeInt | None = None
    span_text: Annotated[str, Field(strict=True, min_length=1)] | None = None


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

    @model_validator(mode="before")
    @classmethod
    def normalize_verdict_payload_shape(cls, data: object) -> object:
        return normalize_verdict_payload(
            data,
            allow_correction=True,
            evidence_max_chars=EVIDENCE_MAX_CHARS,
            default_reject_code="critic_rejected",
        )

    @model_validator(mode="after")
    def validate_decision_fields(self) -> CriticVerdict:
        if self.decision == "accept" and self.code is not None:
            raise ValueError("accepted critic verdicts must not include code")
        if self.decision != "accept" and self.code is None:
            raise ValueError("non-accepted critic verdicts must include code")
        if self.decision != "correct" and self.correction is not None:
            raise ValueError("only corrected critic verdicts may include correction")
        return self


CriticCompactVerdict = tuple[
    NonEmptyStr,
    NonEmptyStr,
    RejectionReasonCode | None,
    Evidence | None,
    CompactCorrection | None,
]


class CriticBatchVerdicts(CriticModel):
    verdicts: tuple[CriticVerdict | CriticCompactVerdict, ...]

    @field_validator("verdicts", mode="before")
    @classmethod
    def normalize_compact_verdicts(
        cls,
        verdicts: object,
    ) -> object:
        verdicts = parse_json_if_string(verdicts)
        if not isinstance(verdicts, (list, tuple)):
            return verdicts
        return tuple(
            normalize_verdict_payload(
                verdict,
                allow_correction=True,
                evidence_max_chars=EVIDENCE_MAX_CHARS,
                default_reject_code="critic_rejected",
            )
            for verdict in verdicts
        )


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
    "CriticCompactVerdict",
    "CriticVerdict",
    "CriticResult",
    "CriticTaskResult",
    "CompactCorrection",
]
