from __future__ import annotations

from collections import Counter
from typing import Any, Literal

from pydantic import Field, model_validator

from extractor.contracts.base import Confidence, ContractModel, NonEmptyStr, NonNegativeInt
from extractor.contracts.base import Sha256Hex, Timestamp
from extractor.contracts.models import SourceSpan


ReportSchemaVersion = Literal[
    "report.v2",
    "refusal.v1",
    "cross_document_report.v1",
    "run_diff_report.v1",
]
ConfidenceBucketName = Literal["verified", "probable", "tentative"]
SignatureAlgorithm = Literal["hmac-sha256"]
AuditIntegrityEventKind = Literal[
    "report_manifest_signed",
    "report_manifest_verified",
    "run_diff_written",
]
RunDiffSide = Literal["base", "candidate"]
RunDiffKind = Literal[
    "added",
    "removed",
    "changed_value",
    "changed_provenance",
    "changed_confidence",
    "unchanged",
    "ambiguous_match",
]
DiffConflictStatus = Literal["none", "unresolved"]


class ReportArtifactRef(ContractModel):
    artifact_path: NonEmptyStr
    report_schema_version: ReportSchemaVersion
    artifact_sha256: Sha256Hex
    byte_length: NonNegativeInt
    run_id: NonEmptyStr | None = None
    doc_id: NonEmptyStr | None = None
    cross_document_run_id: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_run_identity(self) -> ReportArtifactRef:
        if self.run_id is None and self.cross_document_run_id is None:
            raise ValueError("report artifact must include a run identity")
        if self.run_id is not None and self.cross_document_run_id is not None:
            raise ValueError("report artifact must not mix run identity types")
        if self.run_id is not None and self.doc_id is None:
            raise ValueError("single-document report artifacts must include doc_id")
        return self


class ReportConfidenceBucketSummary(ContractModel):
    bucket_name: ConfidenceBucketName
    item_ids: tuple[NonEmptyStr, ...] = ()
    count: NonNegativeInt
    minimum_confidence: Confidence
    maximum_confidence: Confidence

    @model_validator(mode="after")
    def validate_bucket_count_and_range(self) -> ReportConfidenceBucketSummary:
        if self.count != len(self.item_ids):
            raise ValueError("count must match item_ids length")
        if self.minimum_confidence > self.maximum_confidence:
            raise ValueError("minimum_confidence must not exceed maximum_confidence")
        return self


class ReportSignatureEnvelope(ContractModel):
    signature_algorithm: SignatureAlgorithm
    key_id: NonEmptyStr
    signed_payload_sha256: Sha256Hex
    signature: Sha256Hex


class AuditIntegrityEvent(ContractModel):
    event_id: NonEmptyStr
    event_kind: AuditIntegrityEventKind
    run_id: NonEmptyStr | None = None
    cross_document_run_id: NonEmptyStr | None = None
    artifact_sha256: Sha256Hex
    payload_sha256: Sha256Hex
    previous_chain_hash: Sha256Hex | None = None
    chain_hash: Sha256Hex
    created_at: Timestamp
    payload_json: dict[str, Any]

    @model_validator(mode="after")
    def validate_run_identity(self) -> AuditIntegrityEvent:
        if self.run_id is None and self.cross_document_run_id is None:
            raise ValueError("audit integrity events must include a run identity")
        return self


class SignedReportManifest(ContractModel):
    manifest_schema_version: Literal["signed_report_manifest.v1"]
    artifact: ReportArtifactRef
    source_sha256s: tuple[Sha256Hex, ...] = Field(min_length=1)
    text_sha256s: tuple[Sha256Hex, ...] = Field(min_length=1)
    schema_hashes: tuple[Sha256Hex, ...] = ()
    prompt_sha256s: tuple[Sha256Hex, ...] = ()
    config_sha256: Sha256Hex
    confidence_buckets: tuple[ReportConfidenceBucketSummary, ...]
    audit_digest_sha256: Sha256Hex
    audit_chain_head_sha256: Sha256Hex
    signature: ReportSignatureEnvelope


class RunDiffFactRef(ContractModel):
    report_side: RunDiffSide
    run_id: NonEmptyStr
    doc_id: NonEmptyStr
    data_point_id: NonEmptyStr | None = None
    group_id: NonEmptyStr | None = None
    conflict_id: NonEmptyStr | None = None
    category: NonEmptyStr
    field_name: NonEmptyStr
    value: NonEmptyStr
    value_canonical: NonEmptyStr | None = None
    source_span: SourceSpan | None = None
    confidence: Confidence | None = None
    conflict_status: DiffConflictStatus = "none"
    conflict_group_id: NonEmptyStr | None = None
    conflict_reason: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_ref_identity(self) -> RunDiffFactRef:
        identity_count = sum(
            item is not None for item in (self.data_point_id, self.group_id, self.conflict_id)
        )
        if identity_count != 1:
            raise ValueError(
                "run diff fact refs must include exactly one data point, group, or conflict ID"
            )
        return self


class RunDiffEntry(ContractModel):
    diff_entry_id: NonEmptyStr
    diff_kind: RunDiffKind
    old_refs: tuple[RunDiffFactRef, ...] = ()
    new_refs: tuple[RunDiffFactRef, ...] = ()
    reason: NonEmptyStr

    @model_validator(mode="after")
    def validate_refs_for_kind(self) -> RunDiffEntry:
        if self.diff_kind == "added":
            if self.old_refs or not self.new_refs:
                raise ValueError("added entries must include only new refs")
        elif self.diff_kind == "removed":
            if not self.old_refs or self.new_refs:
                raise ValueError("removed entries must include only old refs")
        elif not self.old_refs or not self.new_refs:
            raise ValueError(f"{self.diff_kind} entries must include old and new refs")
        return self


class RunDiffReport(ContractModel):
    report_schema_version: Literal["run_diff_report.v1"]
    diff_run_id: NonEmptyStr
    generated_at: Timestamp
    base_artifact: ReportArtifactRef
    candidate_artifact: ReportArtifactRef
    entries: tuple[RunDiffEntry, ...]
    summary_counts: dict[RunDiffKind, NonNegativeInt]
    signed_manifest_refs: tuple[ReportArtifactRef, ...] = ()

    @model_validator(mode="after")
    def validate_summary_counts(self) -> RunDiffReport:
        expected_keys = set(RunDiffKind.__args__)  # type: ignore[attr-defined]
        if set(self.summary_counts) != expected_keys:
            raise ValueError("summary_counts must include every run diff kind")

        actual_counts = Counter(entry.diff_kind for entry in self.entries)
        expected_counts = {kind: actual_counts.get(kind, 0) for kind in expected_keys}
        if self.summary_counts != expected_counts:
            raise ValueError("summary_counts must match entries by diff kind")
        return self


__all__ = [
    "AuditIntegrityEvent",
    "AuditIntegrityEventKind",
    "ConfidenceBucketName",
    "DiffConflictStatus",
    "ReportArtifactRef",
    "ReportConfidenceBucketSummary",
    "ReportSchemaVersion",
    "ReportSignatureEnvelope",
    "RunDiffEntry",
    "RunDiffFactRef",
    "RunDiffKind",
    "RunDiffReport",
    "RunDiffSide",
    "SignatureAlgorithm",
    "SignedReportManifest",
]
