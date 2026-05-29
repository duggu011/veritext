from __future__ import annotations

from datetime import datetime, timezone
import importlib

from extractor.audit import CandidateRejection
from extractor.contracts import (
    RejectionReason,
    ReportArtifactRef,
    ReportConfidenceBucketSummary,
    ReportSignatureEnvelope,
    SignedReportManifest,
    SourceSpan,
)
from extractor.reporter import diff_reports
from tests.unit.test_phase_40_run_diff import make_report
from tests.unit.test_reporter import HASH, make_data_point, make_document, make_schema_metadata


GENERATED = datetime(2026, 5, 30, 16, 0, tzinfo=timezone.utc)
TEXT_HASH = "b" * 64
PROMPT_HASH = "c" * 64
CONFIG_HASH = "d" * 64


def _builder():
    module = importlib.import_module("extractor.reporter")
    value = getattr(module, "build_static_provenance_artifact", None)
    assert value is not None, "build_static_provenance_artifact must be exported"
    return value


def make_signed_manifest() -> SignedReportManifest:
    bucket = ReportConfidenceBucketSummary(
        bucket_name="verified",
        item_ids=("dp-1",),
        count=1,
        minimum_confidence=0.85,
        maximum_confidence=1.0,
    )
    payload_hash = "e" * 64
    return SignedReportManifest(
        manifest_schema_version="signed_report_manifest.v1",
        artifact=ReportArtifactRef(
            artifact_path="reports/run-1.json",
            report_schema_version="report.v2",
            artifact_sha256=HASH,
            byte_length=512,
            run_id="run-1",
            doc_id="doc-1",
        ),
        source_sha256s=(HASH,),
        text_sha256s=(TEXT_HASH,),
        schema_hashes=(make_schema_metadata().schema_hash,),
        prompt_sha256s=(PROMPT_HASH,),
        config_sha256=CONFIG_HASH,
        confidence_buckets=(bucket,),
        audit_digest_sha256=payload_hash,
        audit_chain_head_sha256=payload_hash,
        signature=ReportSignatureEnvelope(
            signature_algorithm="hmac-sha256",
            key_id="phase-42-key",
            signed_payload_sha256=payload_hash,
            signature=payload_hash,
        ),
    )


def make_rejection() -> CandidateRejection:
    return CandidateRejection(
        rejection_id="rejection-1",
        run_id="run-1",
        candidate_id="candidate-rejected",
        stage="critic",
        reasons=(
            RejectionReason(
                code="critic_rejected",
                message="Critic rejected this candidate.",
            ),
        ),
        created_at=GENERATED,
    )


def test_build_static_artifact_binds_report_manifest_document_rejections_and_diff() -> None:
    build_static_provenance_artifact = _builder()
    point = make_data_point().model_copy(update={"confidence": 0.91})
    report = make_report(run_id="run-1", data_points=(point,))
    changed = make_data_point(
        data_point_id="dp-2",
        value="Margin declined",
        start_char=19,
    ).model_copy(update={"run_id": "run-2"})
    diff_report = diff_reports(
        base_report=report,
        candidate_report=make_report(run_id="run-2", data_points=(changed,)),
        diff_run_id="diff-run-1-run-2",
        generated_at=GENERATED,
    )

    artifact = build_static_provenance_artifact(
        report=report,
        signed_manifest=make_signed_manifest(),
        document=make_document(),
        candidate_rejections=(make_rejection(),),
        diff_report=diff_report,
        generated_at=GENERATED,
        context_radius=8,
    )

    assert artifact.artifact_schema_version == "static_provenance_artifact.v1"
    assert artifact.run_id == "run-1"
    assert artifact.report_artifact.artifact_sha256 == HASH
    assert artifact.manifest_identity.signature_key_id == "phase-42-key"
    assert artifact.document_summary.source_path == "/tmp/doc.txt"
    assert artifact.data_point_views[0].data_point_id == "dp-1"
    assert artifact.data_point_views[0].confidence_bucket == "verified"
    assert artifact.data_point_views[0].source_context.offset_status == "matched"
    assert artifact.rejection_summaries[0].stage == "critic"
    assert artifact.rejection_summaries[0].reason_code == "critic_rejected"
    assert artifact.rejection_summaries[0].candidate_ids == ("candidate-rejected",)
    assert artifact.diff_summary.diff_run_id == "diff-run-1-run-2"


def test_build_static_artifact_marks_absent_optional_trails_explicitly() -> None:
    build_static_provenance_artifact = _builder()
    point = make_data_point().model_copy(update={"confidence": 0.72})
    report = make_report(run_id="run-1", data_points=(point,))

    artifact = build_static_provenance_artifact(
        report=report,
        signed_manifest=None,
        document=None,
        candidate_rejections=(),
        diff_report=None,
        generated_at=GENERATED,
        context_radius=8,
    )

    warning_codes = tuple(warning.warning_code for warning in artifact.warnings)
    assert artifact.manifest_identity is None
    assert artifact.document_summary is None
    assert artifact.diff_summary is None
    assert artifact.data_point_views[0].source_context.offset_status == "document_unavailable"
    assert "signed_manifest_not_supplied" in warning_codes
    assert "audit_document_not_supplied" in warning_codes
    assert "run_diff_not_supplied" in warning_codes


def test_build_static_artifact_preserves_source_mismatch_warning() -> None:
    build_static_provenance_artifact = _builder()
    point = make_data_point().model_copy(
        update={
            "source_span": SourceSpan(
                doc_id="doc-1",
                chunk_id="chunk-1",
                start_char=0,
                end_char=len("Revenue INCREASED"),
                start_byte=0,
                end_byte=len("Revenue INCREASED".encode("utf-8")),
                text="Revenue INCREASED",
            )
        }
    )
    report = make_report(run_id="run-1", data_points=(point,))

    artifact = build_static_provenance_artifact(
        report=report,
        signed_manifest=None,
        document=make_document(),
        candidate_rejections=(),
        diff_report=None,
        generated_at=GENERATED,
        context_radius=8,
    )

    view_warning_codes = tuple(
        warning.warning_code for warning in artifact.data_point_views[0].warnings
    )
    artifact_warning_codes = tuple(warning.warning_code for warning in artifact.warnings)
    assert artifact.data_point_views[0].source_context.offset_status == "mismatched"
    assert "source_span_text_mismatch" in view_warning_codes
    assert "source_span_text_mismatch" in artifact_warning_codes
