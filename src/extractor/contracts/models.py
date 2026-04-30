from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]
Sha256Hex = Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
Confidence = Annotated[float, Field(strict=True, ge=0.0, le=1.0)]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
PositiveInt = Annotated[int, Field(strict=True, ge=1)]
Timestamp = Annotated[datetime, Field(strict=True)]

LensName = Literal["entity", "event", "claim", "number"]
RunStatus = Literal["created", "running", "completed", "failed"]
DocumentFormat = Literal["plain_text", "markdown", "pdf"]
LLMStage = Literal[
    "planner.classify_document",
    "planner.propose_schema",
    "planner.critique_schema",
    "planner.select_strategy",
    "planner.allocate_budget",
    "executor.entity",
    "executor.event",
    "executor.claim",
    "executor.number",
    "critic",
    "verifier",
    "reconciler",
]
RejectionReasonCode = Literal[
    "invalid_source_offsets",
    "invented_span",
    "category_not_approved",
    "critic_rejected",
    "verifier_rejected",
    "reconciler_rejected",
    "schema_violation",
    "ambiguous_source_span",
]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PageSpan(ContractModel):
    page_number: PositiveInt
    start_char: NonNegativeInt
    end_char: NonNegativeInt
    start_byte: NonNegativeInt
    end_byte: NonNegativeInt

    @model_validator(mode="after")
    def validate_offsets(self) -> PageSpan:
        if self.end_char < self.start_char:
            raise ValueError("end_char must be greater than or equal to start_char")
        if self.end_byte < self.start_byte:
            raise ValueError("end_byte must be greater than or equal to start_byte")
        return self


class Document(ContractModel):
    doc_id: NonEmptyStr
    source_path: NonEmptyStr
    format: DocumentFormat
    text: Annotated[str, Field(strict=True)]
    source_sha256: Sha256Hex
    text_sha256: Sha256Hex
    source_byte_length: NonNegativeInt
    text_byte_length: NonNegativeInt
    page_map: tuple[PageSpan, ...] = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def reject_empty_text(cls, value: str) -> str:
        if value == "":
            raise ValueError("text must not be empty")
        return value

    @model_validator(mode="after")
    def validate_page_map(self) -> Document:
        if self.text_byte_length != len(self.text.encode("utf-8")):
            raise ValueError("text_byte_length must match UTF-8 encoded text length")

        previous_char_end = 0
        previous_byte_end = 0
        text_length = len(self.text)
        for page in self.page_map:
            if page.end_char > text_length:
                raise ValueError("page_map entry exceeds document text length")
            if page.end_byte > self.text_byte_length:
                raise ValueError("page_map entry exceeds document text byte length")
            if page.start_char < previous_char_end:
                raise ValueError("page_map character entries must be ordered and non-overlapping")
            if page.start_byte < previous_byte_end:
                raise ValueError("page_map byte entries must be ordered and non-overlapping")
            previous_char_end = page.end_char
            previous_byte_end = page.end_byte
        return self


class Chunk(ContractModel):
    chunk_id: NonEmptyStr
    doc_id: NonEmptyStr
    chunk_index: NonNegativeInt
    text: Annotated[str, Field(strict=True, min_length=1)]
    start_char: NonNegativeInt
    end_char: NonNegativeInt
    start_byte: NonNegativeInt
    end_byte: NonNegativeInt
    start_token: NonNegativeInt
    end_token: NonNegativeInt

    @model_validator(mode="after")
    def validate_offsets(self) -> Chunk:
        if self.end_char <= self.start_char:
            raise ValueError("end_char must be greater than start_char")
        if self.end_byte <= self.start_byte:
            raise ValueError("end_byte must be greater than start_byte")
        if self.end_token <= self.start_token:
            raise ValueError("end_token must be greater than start_token")
        if len(self.text) != self.end_char - self.start_char:
            raise ValueError("chunk text length must match character offsets")
        if len(self.text.encode("utf-8")) != self.end_byte - self.start_byte:
            raise ValueError("chunk text byte length must match byte offsets")
        return self


class SourceSpan(ContractModel):
    doc_id: NonEmptyStr
    chunk_id: NonEmptyStr
    start_char: NonNegativeInt
    end_char: NonNegativeInt
    start_byte: NonNegativeInt
    end_byte: NonNegativeInt
    text: Annotated[str, Field(strict=True, min_length=1)]

    @model_validator(mode="after")
    def validate_offsets(self) -> SourceSpan:
        if self.end_char <= self.start_char:
            raise ValueError("end_char must be greater than start_char")
        if self.end_byte <= self.start_byte:
            raise ValueError("end_byte must be greater than start_byte")
        if len(self.text) != self.end_char - self.start_char:
            raise ValueError("source span text length must match character offsets")
        if len(self.text.encode("utf-8")) != self.end_byte - self.start_byte:
            raise ValueError("source span text byte length must match byte offsets")
        return self


class FieldDefinition(ContractModel):
    name: NonEmptyStr
    description: NonEmptyStr
    value_type: NonEmptyStr
    required: bool = Field(strict=True)


class CategoryDefinition(ContractModel):
    name: NonEmptyStr
    description: NonEmptyStr
    fields: tuple[FieldDefinition, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_field_names(self) -> CategoryDefinition:
        names = [field.name for field in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("category field names must be unique")
        return self


class LensBudget(ContractModel):
    lens: LensName
    max_calls: PositiveInt


class ExtractionBudget(ContractModel):
    per_chunk_concurrency: PositiveInt
    lens_budgets: tuple[LensBudget, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_lens_budgets(self) -> ExtractionBudget:
        lenses = [budget.lens for budget in self.lens_budgets]
        if len(lenses) != len(set(lenses)):
            raise ValueError("lens budgets must be unique by lens")
        return self


class ChunkPolicy(ContractModel):
    window_tokens: PositiveInt
    overlap_tokens: NonNegativeInt

    @model_validator(mode="after")
    def validate_overlap(self) -> ChunkPolicy:
        if self.overlap_tokens >= self.window_tokens:
            raise ValueError("overlap_tokens must be less than window_tokens")
        return self


class ExtractionPlan(ContractModel):
    run_id: NonEmptyStr
    doc_id: NonEmptyStr
    domain_hints: tuple[NonEmptyStr, ...]
    approved_categories: tuple[CategoryDefinition, ...] = Field(min_length=1)
    enabled_lenses: tuple[LensName, ...] = Field(min_length=1)
    chunk_policy: ChunkPolicy
    budget: ExtractionBudget

    @model_validator(mode="after")
    def validate_plan(self) -> ExtractionPlan:
        category_names = [category.name for category in self.approved_categories]
        if len(category_names) != len(set(category_names)):
            raise ValueError("approved category names must be unique")

        if len(self.enabled_lenses) != len(set(self.enabled_lenses)):
            raise ValueError("enabled lenses must be unique")

        budget_lenses = {budget.lens for budget in self.budget.lens_budgets}
        missing_budgets = set(self.enabled_lenses) - budget_lenses
        if missing_budgets:
            raise ValueError("every enabled lens must have a budget")
        return self

    @property
    def approved_category_names(self) -> frozenset[str]:
        return frozenset(category.name for category in self.approved_categories)


class LensCandidate(ContractModel):
    candidate_id: NonEmptyStr
    run_id: NonEmptyStr
    doc_id: NonEmptyStr
    chunk_id: NonEmptyStr
    lens: LensName
    category: NonEmptyStr
    field_name: NonEmptyStr
    value: NonEmptyStr
    source_span: SourceSpan
    confidence: Confidence
    executor_call_id: NonEmptyStr

    @model_validator(mode="after")
    def validate_source_identity(self) -> LensCandidate:
        if self.source_span.doc_id != self.doc_id:
            raise ValueError("source_span doc_id must match candidate doc_id")
        if self.source_span.chunk_id != self.chunk_id:
            raise ValueError("source_span chunk_id must match candidate chunk_id")
        return self


class CriticIssue(ContractModel):
    code: NonEmptyStr
    severity: Literal["low", "medium", "high"]
    message: NonEmptyStr


class CriticReport(ContractModel):
    report_id: NonEmptyStr
    run_id: NonEmptyStr
    candidate_id: NonEmptyStr
    critic_call_id: NonEmptyStr
    plausibility_score: Confidence
    accepted: bool = Field(strict=True)
    issues: tuple[CriticIssue, ...]
    corrected_candidate: LensCandidate | None = None

    @model_validator(mode="after")
    def validate_correction(self) -> CriticReport:
        if self.corrected_candidate is not None:
            if self.corrected_candidate.candidate_id != self.candidate_id:
                raise ValueError("corrected candidate must preserve candidate_id")
            if self.corrected_candidate.run_id != self.run_id:
                raise ValueError("corrected candidate must preserve run_id")
        return self


class RejectionReason(ContractModel):
    code: RejectionReasonCode
    message: NonEmptyStr


class VerifierReport(ContractModel):
    report_id: NonEmptyStr
    run_id: NonEmptyStr
    candidate_id: NonEmptyStr
    verifier_call_id: NonEmptyStr
    span_verified: bool = Field(strict=True)
    category_verified: bool = Field(strict=True)
    alignment_score: Confidence
    accepted: bool = Field(strict=True)
    rejection_reasons: tuple[RejectionReason, ...]

    @model_validator(mode="after")
    def validate_acceptance_reasons(self) -> VerifierReport:
        if self.accepted and self.rejection_reasons:
            raise ValueError("accepted verifier reports must not include rejection reasons")
        if not self.accepted and not self.rejection_reasons:
            raise ValueError("rejected verifier reports must include at least one reason")
        return self


class DataPoint(ContractModel):
    data_point_id: NonEmptyStr
    run_id: NonEmptyStr
    doc_id: NonEmptyStr
    category: NonEmptyStr
    field_name: NonEmptyStr
    value: NonEmptyStr
    source_span: SourceSpan
    confidence: Confidence
    contributing_candidate_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    critic_report_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    verifier_report_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    reconciliation_decision_id: NonEmptyStr

    @model_validator(mode="after")
    def validate_source_identity(self) -> DataPoint:
        if self.source_span.doc_id != self.doc_id:
            raise ValueError("source_span doc_id must match data point doc_id")
        return self


class RunManifest(ContractModel):
    run_id: NonEmptyStr
    doc_id: NonEmptyStr
    audit_db_path: NonEmptyStr
    status: RunStatus
    started_at: Timestamp
    completed_at: Timestamp | None = None
    output_data_point_ids: tuple[NonEmptyStr, ...]

    @model_validator(mode="after")
    def validate_completion_time(self) -> RunManifest:
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at must not be earlier than started_at")
        if self.status == "completed" and self.completed_at is None:
            raise ValueError("completed runs must include completed_at")
        return self


class LLMCallLog(ContractModel):
    call_id: NonEmptyStr
    run_id: NonEmptyStr
    stage: LLMStage
    attempt: PositiveInt
    model: NonEmptyStr
    prompt_sha256: Sha256Hex
    input_tokens: NonNegativeInt
    output_tokens: NonNegativeInt
    cache_read_tokens: NonNegativeInt
    cache_creation_tokens: NonNegativeInt
    latency_ms: NonNegativeInt
    stop_reason: NonEmptyStr
    tool_name: NonEmptyStr
    created_at: Timestamp


__all__ = [
    "CategoryDefinition",
    "Chunk",
    "ChunkPolicy",
    "CriticIssue",
    "CriticReport",
    "DataPoint",
    "Document",
    "ExtractionBudget",
    "ExtractionPlan",
    "FieldDefinition",
    "LLMCallLog",
    "LensBudget",
    "LensCandidate",
    "PageSpan",
    "RejectionReason",
    "RunManifest",
    "SourceSpan",
    "VerifierReport",
]
