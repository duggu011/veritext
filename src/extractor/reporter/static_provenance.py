from __future__ import annotations

from datetime import datetime

from extractor.audit import CandidateRejection
from extractor.contracts import (
    DataPoint,
    Document,
    RunDiffReport,
    SignedReportManifest,
    StaticProvenanceArtifact,
    StaticProvenanceDataPointView,
    StaticProvenanceDiffSummary,
    StaticProvenanceDocumentSummary,
    StaticProvenanceManifestIdentity,
    StaticProvenanceRejectionSummary,
    StaticProvenanceWarning,
    build_static_source_context,
)
from extractor.contracts.report_integrity import ConfidenceBucketName
from extractor.reporter.models import ExtractionReport


def build_static_provenance_artifact(
    *,
    report: ExtractionReport,
    signed_manifest: SignedReportManifest | None,
    document: Document | None,
    candidate_rejections: tuple[CandidateRejection, ...],
    diff_report: RunDiffReport | None,
    generated_at: datetime | None,
    context_radius: int,
) -> StaticProvenanceArtifact:
    warnings: list[StaticProvenanceWarning] = []
    manifest_identity = _manifest_identity(signed_manifest)
    if signed_manifest is None:
        warnings.append(
            _warning(
                "signed_manifest_not_supplied",
                "low",
                "Signed report manifest was not supplied.",
            )
        )

    document_summary = _document_summary(document)
    document_text = None
    if document is None:
        warnings.append(
            _warning(
                "audit_document_not_supplied",
                "medium",
                "Audited document text was not supplied.",
            )
        )
    elif document.doc_id != report.doc_id:
        warnings.append(
            _warning(
                "audit_document_doc_id_mismatch",
                "high",
                "Audited document ID does not match the report document ID.",
            )
        )
    else:
        document_text = document.text

    diff_summary = _diff_summary(diff_report)
    if diff_report is None:
        warnings.append(
            _warning(
                "run_diff_not_supplied",
                "low",
                "Run diff report was not supplied.",
            )
        )

    confidence_buckets = _confidence_bucket_map(signed_manifest)
    views: list[StaticProvenanceDataPointView] = []
    for data_point in report.data_points:
        view = _data_point_view(
            data_point=data_point,
            document_text=document_text,
            confidence_buckets=confidence_buckets,
            context_radius=context_radius,
        )
        views.append(view)
        warnings.extend(view.warnings)

    return StaticProvenanceArtifact(
        artifact_schema_version="static_provenance_artifact.v1",
        run_id=report.run_id,
        doc_id=report.doc_id,
        report_schema_version=report.report_schema_version,
        generated_at=generated_at or report.generated_at,
        report_artifact=signed_manifest.artifact if signed_manifest is not None else None,
        schema_id=report.schema_metadata.schema_id,
        schema_hash=report.schema_metadata.schema_hash,
        schema_source_kind=report.schema_metadata.source_kind,
        output_data_point_ids=report.output_data_point_ids,
        manifest_identity=manifest_identity,
        document_summary=document_summary,
        data_point_views=tuple(views),
        rejection_summaries=_rejection_summaries(candidate_rejections),
        diff_summary=diff_summary,
        warnings=tuple(warnings),
    )


def _data_point_view(
    *,
    data_point: DataPoint,
    document_text: str | None,
    confidence_buckets: dict[str, ConfidenceBucketName],
    context_radius: int,
) -> StaticProvenanceDataPointView:
    source_context = build_static_source_context(
        data_point_id=data_point.data_point_id,
        source_span=data_point.source_span,
        document_text=document_text,
        context_radius=context_radius,
    )
    return StaticProvenanceDataPointView(
        data_point_id=data_point.data_point_id,
        category=data_point.category,
        field_name=data_point.field_name,
        value=data_point.value,
        value_canonical=data_point.value_canonical,
        value_kind=data_point.value_kind,
        confidence=data_point.confidence,
        confidence_bucket=confidence_buckets.get(data_point.data_point_id),
        conflict_status=data_point.conflict_status,
        conflict_group_id=data_point.conflict_group_id,
        conflict_reason=data_point.conflict_reason,
        source_context=source_context,
        contributing_candidate_ids=data_point.contributing_candidate_ids,
        critic_report_ids=data_point.critic_report_ids,
        verifier_report_ids=data_point.verifier_report_ids,
        reconciliation_decision_id=data_point.reconciliation_decision_id,
        warnings=source_context.warnings,
    )


def _manifest_identity(
    signed_manifest: SignedReportManifest | None,
) -> StaticProvenanceManifestIdentity | None:
    if signed_manifest is None:
        return None
    return StaticProvenanceManifestIdentity(
        artifact=signed_manifest.artifact,
        source_sha256s=signed_manifest.source_sha256s,
        text_sha256s=signed_manifest.text_sha256s,
        schema_hashes=signed_manifest.schema_hashes,
        prompt_sha256s=signed_manifest.prompt_sha256s,
        config_sha256=signed_manifest.config_sha256,
        audit_digest_sha256=signed_manifest.audit_digest_sha256,
        audit_chain_head_sha256=signed_manifest.audit_chain_head_sha256,
        signature_key_id=signed_manifest.signature.key_id,
        confidence_buckets=signed_manifest.confidence_buckets,
    )


def _document_summary(document: Document | None) -> StaticProvenanceDocumentSummary | None:
    if document is None:
        return None
    return StaticProvenanceDocumentSummary(
        doc_id=document.doc_id,
        source_path=document.source_path,
        format=document.format,
        source_sha256=document.source_sha256,
        text_sha256=document.text_sha256,
        source_byte_length=document.source_byte_length,
        text_byte_length=document.text_byte_length,
        page_count=len(document.page_map),
    )


def _diff_summary(diff_report: RunDiffReport | None) -> StaticProvenanceDiffSummary | None:
    if diff_report is None:
        return None
    return StaticProvenanceDiffSummary(
        diff_run_id=diff_report.diff_run_id,
        summary_counts=dict(diff_report.summary_counts),
    )


def _rejection_summaries(
    candidate_rejections: tuple[CandidateRejection, ...],
) -> tuple[StaticProvenanceRejectionSummary, ...]:
    grouped: dict[tuple[str, str], set[str]] = {}
    for rejection in candidate_rejections:
        for reason in rejection.reasons:
            grouped.setdefault((rejection.stage, reason.code), set()).add(
                rejection.candidate_id
            )
    return tuple(
        StaticProvenanceRejectionSummary(
            stage=stage,
            reason_code=reason_code,
            count=len(candidate_ids),
            candidate_ids=tuple(sorted(candidate_ids)),
        )
        for (stage, reason_code), candidate_ids in sorted(grouped.items())
    )


def _confidence_bucket_map(
    signed_manifest: SignedReportManifest | None,
) -> dict[str, ConfidenceBucketName]:
    if signed_manifest is None:
        return {}
    return {
        data_point_id: bucket.bucket_name
        for bucket in signed_manifest.confidence_buckets
        for data_point_id in bucket.item_ids
    }


def _warning(
    warning_code: str,
    severity,
    message: str,
) -> StaticProvenanceWarning:
    return StaticProvenanceWarning(
        warning_code=warning_code,
        severity=severity,
        message=message,
    )


__all__ = ["build_static_provenance_artifact"]
