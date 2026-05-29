from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from extractor.contracts.base import (
    Confidence,
    ContractModel,
    DocumentFormat,
    NonEmptyStr,
    NonNegativeInt,
    PositiveInt,
    Sha256Hex,
    Timestamp,
)
from extractor.contracts.models import SourceSpan
from extractor.contracts.normalization import ValueKind
from extractor.contracts.report_integrity import (
    ConfidenceBucketName,
    ReportArtifactRef,
    ReportConfidenceBucketSummary,
    ReportSchemaVersion,
    RunDiffKind,
)
from extractor.contracts.schema_metadata import SchemaSourceKind


Text = Annotated[str, Field(strict=True)]
StaticProvenanceWarningSeverity = Literal["low", "medium", "high"]
StaticProvenanceOffsetStatus = Literal["matched", "mismatched", "document_unavailable"]
StaticProvenanceArtifactSchemaVersion = Literal["static_provenance_artifact.v1"]
StaticProvenanceConflictStatus = Literal["none", "unresolved"]


class StaticProvenanceWarning(ContractModel):
    warning_code: NonEmptyStr
    severity: StaticProvenanceWarningSeverity
    message: NonEmptyStr
    data_point_id: NonEmptyStr | None = None
    source_span: SourceSpan | None = None


class StaticProvenanceSourceContext(ContractModel):
    data_point_id: NonEmptyStr
    source_span: SourceSpan
    prefix_text: Text
    highlighted_text: Text
    suffix_text: Text
    offset_status: StaticProvenanceOffsetStatus
    mismatch_expected_text: Text | None = None
    mismatch_actual_text: Text | None = None
    warnings: tuple[StaticProvenanceWarning, ...] = ()

    @model_validator(mode="after")
    def validate_context_consistency(self) -> StaticProvenanceSourceContext:
        if self.offset_status == "matched":
            if self.highlighted_text != self.source_span.text:
                raise ValueError("matched source context must preserve source_span text")
            if self.mismatch_expected_text is not None or self.mismatch_actual_text is not None:
                raise ValueError("matched source context must not include mismatch text")
        elif self.offset_status == "mismatched":
            if self.mismatch_expected_text != self.source_span.text:
                raise ValueError("mismatch_expected_text must preserve source_span text")
            if self.mismatch_actual_text != self.highlighted_text:
                raise ValueError("mismatch_actual_text must match highlighted_text")
            if not self.warnings:
                raise ValueError("mismatched source context must include a warning")
        else:
            if self.highlighted_text != self.source_span.text:
                raise ValueError("document-unavailable context must preserve source_span text")
            if self.mismatch_expected_text is not None or self.mismatch_actual_text is not None:
                raise ValueError("document-unavailable context must not include mismatch text")
            if not self.warnings:
                raise ValueError("document-unavailable source context must include a warning")
        return self


class StaticProvenanceDataPointView(ContractModel):
    data_point_id: NonEmptyStr
    category: NonEmptyStr
    field_name: NonEmptyStr
    value: NonEmptyStr
    value_canonical: NonEmptyStr | None = None
    value_kind: ValueKind = "text"
    confidence: Confidence
    confidence_bucket: ConfidenceBucketName | None = None
    conflict_status: StaticProvenanceConflictStatus = "none"
    conflict_group_id: NonEmptyStr | None = None
    conflict_reason: NonEmptyStr | None = None
    source_context: StaticProvenanceSourceContext
    contributing_candidate_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    critic_report_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    verifier_report_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    reconciliation_decision_id: NonEmptyStr
    warnings: tuple[StaticProvenanceWarning, ...] = ()

    @model_validator(mode="after")
    def validate_view_identity(self) -> StaticProvenanceDataPointView:
        if self.source_context.data_point_id != self.data_point_id:
            raise ValueError("source_context data_point_id must match data point view")
        for warning in self.warnings:
            if warning.data_point_id not in {None, self.data_point_id}:
                raise ValueError("warning data_point_id must match data point view")
        return self


class StaticProvenanceManifestIdentity(ContractModel):
    artifact: ReportArtifactRef
    source_sha256s: tuple[Sha256Hex, ...] = Field(min_length=1)
    text_sha256s: tuple[Sha256Hex, ...] = Field(min_length=1)
    schema_hashes: tuple[Sha256Hex, ...] = ()
    prompt_sha256s: tuple[Sha256Hex, ...] = ()
    config_sha256: Sha256Hex
    audit_digest_sha256: Sha256Hex
    audit_chain_head_sha256: Sha256Hex
    signature_key_id: NonEmptyStr
    confidence_buckets: tuple[ReportConfidenceBucketSummary, ...] = ()


class StaticProvenanceDocumentSummary(ContractModel):
    doc_id: NonEmptyStr
    source_path: NonEmptyStr
    format: DocumentFormat
    source_sha256: Sha256Hex
    text_sha256: Sha256Hex
    source_byte_length: NonNegativeInt
    text_byte_length: NonNegativeInt
    page_count: PositiveInt


class StaticProvenanceRejectionSummary(ContractModel):
    stage: NonEmptyStr
    reason_code: NonEmptyStr
    count: NonNegativeInt
    candidate_ids: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_count(self) -> StaticProvenanceRejectionSummary:
        if self.count != len(self.candidate_ids):
            raise ValueError("count must match candidate_ids length")
        return self


class StaticProvenanceDiffSummary(ContractModel):
    diff_run_id: NonEmptyStr
    summary_counts: dict[RunDiffKind, NonNegativeInt]


class StaticProvenanceArtifact(ContractModel):
    artifact_schema_version: StaticProvenanceArtifactSchemaVersion
    run_id: NonEmptyStr
    doc_id: NonEmptyStr
    report_schema_version: ReportSchemaVersion
    generated_at: Timestamp
    report_artifact: ReportArtifactRef | None = None
    schema_id: NonEmptyStr
    schema_hash: Sha256Hex
    schema_source_kind: SchemaSourceKind
    output_data_point_ids: tuple[NonEmptyStr, ...]
    manifest_identity: StaticProvenanceManifestIdentity | None = None
    document_summary: StaticProvenanceDocumentSummary | None = None
    data_point_views: tuple[StaticProvenanceDataPointView, ...]
    rejection_summaries: tuple[StaticProvenanceRejectionSummary, ...] = ()
    diff_summary: StaticProvenanceDiffSummary | None = None
    warnings: tuple[StaticProvenanceWarning, ...] = ()

    @model_validator(mode="after")
    def validate_view_order(self) -> StaticProvenanceArtifact:
        view_ids = tuple(view.data_point_id for view in self.data_point_views)
        if view_ids != self.output_data_point_ids:
            raise ValueError("output_data_point_ids must match data point view order")
        if len(view_ids) != len(set(view_ids)):
            raise ValueError("static provenance data point IDs must be unique")
        return self


def build_static_source_context(
    *,
    data_point_id: str,
    source_span: SourceSpan,
    document_text: str | None,
    context_radius: int,
) -> StaticProvenanceSourceContext:
    if context_radius < 0:
        raise ValueError("context_radius must be non-negative")

    if document_text is None:
        warning = StaticProvenanceWarning(
            warning_code="document_text_unavailable",
            severity="medium",
            message="Audited document text was not available for source context.",
            data_point_id=data_point_id,
            source_span=source_span,
        )
        return StaticProvenanceSourceContext(
            data_point_id=data_point_id,
            source_span=source_span,
            prefix_text="",
            highlighted_text=source_span.text,
            suffix_text="",
            offset_status="document_unavailable",
            warnings=(warning,),
        )

    start_char = source_span.start_char
    end_char = source_span.end_char
    in_bounds = 0 <= start_char <= end_char <= len(document_text)
    actual_text = document_text[start_char:end_char] if in_bounds else ""
    prefix_text = document_text[max(0, start_char - context_radius) : start_char] if in_bounds else ""
    suffix_text = document_text[end_char : min(len(document_text), end_char + context_radius)] if in_bounds else ""

    if actual_text == source_span.text:
        return StaticProvenanceSourceContext(
            data_point_id=data_point_id,
            source_span=source_span,
            prefix_text=prefix_text,
            highlighted_text=actual_text,
            suffix_text=suffix_text,
            offset_status="matched",
            warnings=(),
        )

    warning = StaticProvenanceWarning(
        warning_code="source_span_text_mismatch",
        severity="high",
        message="Source span text does not match the audited document slice.",
        data_point_id=data_point_id,
        source_span=source_span,
    )
    return StaticProvenanceSourceContext(
        data_point_id=data_point_id,
        source_span=source_span,
        prefix_text=prefix_text,
        highlighted_text=actual_text,
        suffix_text=suffix_text,
        offset_status="mismatched",
        mismatch_expected_text=source_span.text,
        mismatch_actual_text=actual_text,
        warnings=(warning,),
    )


__all__ = [
    "StaticProvenanceArtifact",
    "StaticProvenanceArtifactSchemaVersion",
    "StaticProvenanceDataPointView",
    "StaticProvenanceDiffSummary",
    "StaticProvenanceDocumentSummary",
    "StaticProvenanceManifestIdentity",
    "StaticProvenanceOffsetStatus",
    "StaticProvenanceRejectionSummary",
    "StaticProvenanceSourceContext",
    "StaticProvenanceWarning",
    "StaticProvenanceWarningSeverity",
    "build_static_source_context",
]
