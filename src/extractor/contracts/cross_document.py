from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from extractor.contracts.base import (
    ContractModel,
    NonEmptyStr,
    PositiveInt,
    Sha256Hex,
    Timestamp,
)
from extractor.contracts.dedup import CanonicalValueKey
from extractor.contracts.models import SourceSpan
from extractor.contracts.normalization import (
    NormalizationStatus,
    ValueKind,
    validate_normalization_metadata,
)


CrossDocumentRunStatus = Literal["created", "running", "completed", "failed"]
CrossDocumentConflictStatus = Literal["none", "unresolved"]


class CrossDocumentSourceRef(ContractModel):
    run_id: NonEmptyStr
    doc_id: NonEmptyStr
    data_point_id: NonEmptyStr
    source_span: SourceSpan
    supporting_source_spans: tuple[SourceSpan, ...] = ()
    conflict_status: CrossDocumentConflictStatus = "none"
    conflict_group_id: NonEmptyStr | None = None
    conflict_reason: NonEmptyStr | None = None
    source_sha256: Sha256Hex
    text_sha256: Sha256Hex
    value: NonEmptyStr
    value_verbatim: NonEmptyStr | None = None
    value_canonical: NonEmptyStr | None = None
    value_kind: ValueKind = "text"
    normalization_status: NormalizationStatus = "not_normalized"
    normalization_policy_id: NonEmptyStr | None = None
    normalization_policy_version: NonEmptyStr | None = None
    normalization_notes: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_provenance(self) -> CrossDocumentSourceRef:
        if self.source_span.doc_id != self.doc_id:
            raise ValueError("source_span doc_id must match source ref doc_id")
        for span in self.supporting_source_spans:
            if span.doc_id != self.doc_id:
                raise ValueError("supporting_source_spans doc_id must match source ref doc_id")
        if self.conflict_status == "none" and (
            self.conflict_group_id is not None or self.conflict_reason is not None
        ):
            raise ValueError("conflict details require unresolved conflict_status")
        if self.conflict_status == "unresolved" and (
            self.conflict_group_id is None or self.conflict_reason is None
        ):
            raise ValueError("unresolved conflict_status requires conflict details")
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


class CrossDocumentFactKey(ContractModel):
    schema_id: NonEmptyStr | None = None
    schema_hash: Sha256Hex | None = None
    category: NonEmptyStr
    field_name: NonEmptyStr
    canonical_key: CanonicalValueKey
    policy_id: NonEmptyStr | None = None
    policy_version: NonEmptyStr | None = None


class CrossDocumentFactGroup(ContractModel):
    group_id: NonEmptyStr
    key: CrossDocumentFactKey
    sources: tuple[CrossDocumentSourceRef, ...] = Field(min_length=1)
    document_count: PositiveInt
    conflict_status: CrossDocumentConflictStatus = "none"
    conflict_ids: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_group_consistency(self) -> CrossDocumentFactGroup:
        doc_ids = tuple(source.doc_id for source in self.sources)
        if self.document_count != len(set(doc_ids)):
            raise ValueError("document_count must equal unique source document count")
        if len(self.conflict_ids) != len(set(self.conflict_ids)):
            raise ValueError("conflict_ids must be unique")
        if self.conflict_status == "none" and self.conflict_ids:
            raise ValueError("conflict_ids require unresolved conflict_status")
        return self


class CrossDocumentConflict(ContractModel):
    conflict_id: NonEmptyStr
    category: NonEmptyStr
    field_name: NonEmptyStr
    conflicting_group_ids: tuple[NonEmptyStr, ...] = Field(min_length=2)
    reason: NonEmptyStr
    doc_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    canonical_key_identities: tuple[tuple[object, ...], ...] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_conflict_identity(self) -> CrossDocumentConflict:
        if len(self.conflicting_group_ids) != len(set(self.conflicting_group_ids)):
            raise ValueError("conflicting_group_ids must be unique")
        if len(self.doc_ids) != len(set(self.doc_ids)):
            raise ValueError("doc_ids must be unique")
        return self


class CrossDocumentSkippedInput(ContractModel):
    input_id: NonEmptyStr
    input_kind: Literal["run", "document", "data_point"]
    reason: NonEmptyStr


class CrossDocumentReconciliationResult(ContractModel):
    cross_document_run_id: NonEmptyStr
    input_run_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    input_doc_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    groups: tuple[CrossDocumentFactGroup, ...]
    conflicts: tuple[CrossDocumentConflict, ...]
    skipped_inputs: tuple[CrossDocumentSkippedInput, ...] = ()

    @model_validator(mode="after")
    def validate_result_inputs(self) -> CrossDocumentReconciliationResult:
        if len(self.input_run_ids) != len(set(self.input_run_ids)):
            raise ValueError("input_run_ids must be unique")
        if len(self.input_doc_ids) != len(set(self.input_doc_ids)):
            raise ValueError("input_doc_ids must be unique")
        if len(self.groups) != len({group.group_id for group in self.groups}):
            raise ValueError("groups must be unique by group_id")
        if len(self.conflicts) != len({conflict.conflict_id for conflict in self.conflicts}):
            raise ValueError("conflicts must be unique by conflict_id")
        return self


class CrossDocumentRunManifest(ContractModel):
    cross_document_run_id: NonEmptyStr
    audit_db_path: NonEmptyStr
    status: CrossDocumentRunStatus
    started_at: Timestamp
    completed_at: Timestamp | None = None
    input_run_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    output_group_ids: tuple[NonEmptyStr, ...]
    output_conflict_ids: tuple[NonEmptyStr, ...]

    @model_validator(mode="after")
    def validate_manifest(self) -> CrossDocumentRunManifest:
        if len(self.input_run_ids) != len(set(self.input_run_ids)):
            raise ValueError("input_run_ids must be unique")
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at must not be earlier than started_at")
        if self.status in {"completed", "failed"} and self.completed_at is None:
            raise ValueError("completed or failed manifests must include completed_at")
        return self


__all__ = [
    "CrossDocumentConflict",
    "CrossDocumentConflictStatus",
    "CrossDocumentFactGroup",
    "CrossDocumentFactKey",
    "CrossDocumentReconciliationResult",
    "CrossDocumentRunManifest",
    "CrossDocumentRunStatus",
    "CrossDocumentSkippedInput",
    "CrossDocumentSourceRef",
]
