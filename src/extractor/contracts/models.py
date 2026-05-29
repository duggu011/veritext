from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from extractor.contracts.base import (
    Confidence,
    ContractModel,
    DocumentFormat,
    LLMStage,
    LensName,
    NonEmptyStr,
    NonNegativeInt,
    PositiveInt,
    RejectionReasonCode,
    RunStatus,
    Sha256Hex,
    Timestamp,
)
from extractor.contracts.documents import Document, PageSpan
from extractor.contracts.normalization import (
    NormalizationStatus,
    ValueKind,
    validate_normalization_metadata,
)
from extractor.contracts.schema_metadata import (
    ApprovedSchemaMetadata,
    build_planner_generated_schema_metadata,
    canonical_schema_hash,
)

ChunkKind = Literal["document", "section", "paragraph", "list_item", "table", "mixed", "overflow"]
ChunkSplitReason = Literal[
    "boundary",
    "token_window",
    "atomic_table_overflow",
    "oversized_sentence",
    "oversized_paragraph",
    "overlap_adjusted",
]
ChunkTokenizerPolicy = Literal["tiktoken"]


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
    chunk_kind: ChunkKind = "mixed"
    section_path: tuple[NonEmptyStr, ...] = ()
    layout_span_ids: tuple[NonEmptyStr, ...] = ()
    table_ids: tuple[NonEmptyStr, ...] = ()
    page_numbers: tuple[PositiveInt, ...] = ()
    parent_chunk_id: NonEmptyStr | None = None
    depends_on_chunk_ids: tuple[NonEmptyStr, ...] = ()
    split_reason: ChunkSplitReason = "token_window"
    tokenizer_policy: ChunkTokenizerPolicy = "tiktoken"

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
    schema_metadata: ApprovedSchemaMetadata
    enabled_lenses: tuple[LensName, ...] = Field(min_length=1)
    chunk_policy: ChunkPolicy
    budget: ExtractionBudget

    @model_validator(mode="before")
    @classmethod
    def attach_default_schema_metadata(cls, data: object) -> object:
        if not isinstance(data, dict) or data.get("schema_metadata") is not None:
            return data

        categories = tuple(
            CategoryDefinition.model_validate(category)
            for category in data.get("approved_categories", ())
        )
        copied = dict(data)
        copied["schema_metadata"] = build_planner_generated_schema_metadata(
            approved_categories=categories,
            domain_hints=tuple(data.get("domain_hints", ())),
        )
        return copied

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

        expected_schema_hash = canonical_schema_hash(
            approved_categories=self.approved_categories,
            source_kind=self.schema_metadata.source_kind,
            schema_version=self.schema_metadata.schema_version,
            domain_hints=self.domain_hints,
            domain_pack_id=self.schema_metadata.domain_pack_id,
            document_class=self.schema_metadata.document_class,
        )
        if self.schema_metadata.schema_hash != expected_schema_hash:
            raise ValueError("schema_metadata schema_hash must match approved schema")
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
    value_verbatim: NonEmptyStr | None = None
    value_canonical: NonEmptyStr | None = None
    value_kind: ValueKind = "text"
    normalization_status: NormalizationStatus = "not_normalized"
    normalization_policy_id: NonEmptyStr | None = None
    normalization_policy_version: NonEmptyStr | None = None
    normalization_notes: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_source_identity(self) -> LensCandidate:
        if self.source_span.doc_id != self.doc_id:
            raise ValueError("source_span doc_id must match candidate doc_id")
        if self.source_span.chunk_id != self.chunk_id:
            raise ValueError("source_span chunk_id must match candidate chunk_id")
        validate_normalization_metadata(
            value=self.value,
            value_verbatim=self.value_verbatim,
            value_canonical=self.value_canonical,
            normalization_status=self.normalization_status,
            normalization_policy_id=self.normalization_policy_id,
            normalization_policy_version=self.normalization_policy_version,
            normalization_notes=self.normalization_notes,
        )
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
    value_verbatim: NonEmptyStr | None = None
    value_canonical: NonEmptyStr | None = None
    value_kind: ValueKind = "text"
    normalization_status: NormalizationStatus = "not_normalized"
    normalization_policy_id: NonEmptyStr | None = None
    normalization_policy_version: NonEmptyStr | None = None
    normalization_notes: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_source_identity(self) -> DataPoint:
        if self.source_span.doc_id != self.doc_id:
            raise ValueError("source_span doc_id must match data point doc_id")
        validate_normalization_metadata(
            value=self.value,
            value_verbatim=self.value_verbatim,
            value_canonical=self.value_canonical,
            normalization_status=self.normalization_status,
            normalization_policy_id=self.normalization_policy_id,
            normalization_policy_version=self.normalization_policy_version,
            normalization_notes=self.normalization_notes,
        )
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
        if self.status in {"completed", "refused"} and self.completed_at is None:
            raise ValueError("completed or refused runs must include completed_at")
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
    "ChunkKind",
    "ChunkPolicy",
    "ChunkSplitReason",
    "ChunkTokenizerPolicy",
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
