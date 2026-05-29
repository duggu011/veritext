from __future__ import annotations

import importlib
from datetime import datetime, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from extractor.contracts import SourceSpan


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
HASH_D = "d" * 64
GENERATED = datetime(2026, 5, 30, 9, 0, tzinfo=timezone.utc)


def _contract(name: str) -> Any:
    contracts = importlib.import_module("extractor.contracts")
    value = getattr(contracts, name, None)
    assert value is not None, f"{name} must be exported from extractor.contracts"
    return value


def make_source_span(text: str = "Payment is due in 30 days.") -> SourceSpan:
    return SourceSpan(
        doc_id="doc-1",
        chunk_id="chunk-1",
        start_char=0,
        end_char=len(text),
        start_byte=0,
        end_byte=len(text.encode("utf-8")),
        text=text,
    )


def make_artifact_ref(**overrides: object) -> Any:
    ReportArtifactRef = _contract("ReportArtifactRef")
    values: dict[str, object] = {
        "artifact_path": "reports/run-1.json",
        "report_schema_version": "report.v2",
        "artifact_sha256": HASH_A,
        "byte_length": 512,
        "run_id": "run-1",
        "doc_id": "doc-1",
    }
    values.update(overrides)
    return ReportArtifactRef(**values)


def make_bucket(**overrides: object) -> Any:
    ReportConfidenceBucketSummary = _contract("ReportConfidenceBucketSummary")
    values: dict[str, object] = {
        "bucket_name": "verified",
        "item_ids": ("dp-1", "dp-2"),
        "count": 2,
        "minimum_confidence": 0.85,
        "maximum_confidence": 1.0,
    }
    values.update(overrides)
    return ReportConfidenceBucketSummary(**values)


def make_signature(**overrides: object) -> Any:
    ReportSignatureEnvelope = _contract("ReportSignatureEnvelope")
    values: dict[str, object] = {
        "signature_algorithm": "hmac-sha256",
        "key_id": "phase-40-test-key",
        "signed_payload_sha256": HASH_C,
        "signature": HASH_D,
    }
    values.update(overrides)
    return ReportSignatureEnvelope(**values)


def make_fact_ref(**overrides: object) -> Any:
    RunDiffFactRef = _contract("RunDiffFactRef")
    values: dict[str, object] = {
        "report_side": "base",
        "run_id": "run-1",
        "doc_id": "doc-1",
        "data_point_id": "dp-1",
        "category": "PaymentTerm",
        "field_name": "payment_due",
        "value": "30 days",
        "value_canonical": "P30D",
        "source_span": make_source_span(),
        "confidence": 0.93,
        "conflict_status": "none",
        "conflict_group_id": None,
        "conflict_reason": None,
    }
    values.update(overrides)
    return RunDiffFactRef(**values)


def test_signed_report_manifest_binds_report_hashes_and_signature() -> None:
    SignedReportManifest = _contract("SignedReportManifest")

    manifest = SignedReportManifest(
        manifest_schema_version="signed_report_manifest.v1",
        artifact=make_artifact_ref(),
        source_sha256s=(HASH_A,),
        text_sha256s=(HASH_B,),
        schema_hashes=(HASH_C,),
        prompt_sha256s=(HASH_D,),
        config_sha256=HASH_A,
        confidence_buckets=(make_bucket(),),
        audit_digest_sha256=HASH_B,
        audit_chain_head_sha256=HASH_C,
        signature=make_signature(),
    )

    assert manifest.artifact.run_id == "run-1"
    assert manifest.artifact.doc_id == "doc-1"
    assert manifest.signature.signature_algorithm == "hmac-sha256"
    assert manifest.confidence_buckets[0].item_ids == ("dp-1", "dp-2")

    with pytest.raises(ValidationError, match="count"):
        make_bucket(count=3)

    with pytest.raises(ValidationError):
        SignedReportManifest(
            manifest_schema_version="signed_report_manifest.v1",
            artifact=make_artifact_ref(),
            source_sha256s=(HASH_A,),
            text_sha256s=(HASH_B,),
            schema_hashes=(HASH_C,),
            prompt_sha256s=(HASH_D,),
            config_sha256=HASH_A,
            confidence_buckets=(make_bucket(),),
            audit_digest_sha256=HASH_B,
            audit_chain_head_sha256=HASH_C,
            signature=make_signature(signature_algorithm="ed25519"),
        )


def test_audit_integrity_event_records_chain_hash_and_payload() -> None:
    AuditIntegrityEvent = _contract("AuditIntegrityEvent")

    event = AuditIntegrityEvent(
        event_id="aie-report-1",
        event_kind="report_manifest_signed",
        run_id="run-1",
        cross_document_run_id=None,
        artifact_sha256=HASH_A,
        payload_sha256=HASH_B,
        previous_chain_hash=None,
        chain_hash=HASH_C,
        created_at=GENERATED,
        payload_json={"manifest_schema_version": "signed_report_manifest.v1"},
    )

    assert event.run_id == "run-1"
    assert event.previous_chain_hash is None
    assert event.payload_json["manifest_schema_version"] == "signed_report_manifest.v1"

    with pytest.raises(ValidationError, match="run identity"):
        AuditIntegrityEvent(
            event_id="aie-no-run",
            event_kind="report_manifest_signed",
            run_id=None,
            cross_document_run_id=None,
            artifact_sha256=HASH_A,
            payload_sha256=HASH_B,
            previous_chain_hash=None,
            chain_hash=HASH_C,
            created_at=GENERATED,
            payload_json={},
        )


def test_run_diff_report_accounts_for_changed_and_ambiguous_entries() -> None:
    RunDiffEntry = _contract("RunDiffEntry")
    RunDiffReport = _contract("RunDiffReport")

    old_ref = make_fact_ref(report_side="base", value="30 days", value_canonical="P30D")
    new_ref = make_fact_ref(
        report_side="candidate",
        run_id="run-2",
        data_point_id="dp-2",
        value="45 days",
        value_canonical="P45D",
    )
    changed = RunDiffEntry(
        diff_entry_id="diff-changed-payment-due",
        diff_kind="changed_value",
        old_refs=(old_ref,),
        new_refs=(new_ref,),
        reason="canonical_value_changed",
    )
    ambiguous = RunDiffEntry(
        diff_entry_id="diff-ambiguous-payment-due",
        diff_kind="ambiguous_match",
        old_refs=(old_ref,),
        new_refs=(new_ref, make_fact_ref(report_side="candidate", data_point_id="dp-3")),
        reason="multiple_candidate_matches",
    )
    report = RunDiffReport(
        report_schema_version="run_diff_report.v1",
        diff_run_id="diff-run-1-run-2",
        generated_at=GENERATED,
        base_artifact=make_artifact_ref(run_id="run-1", artifact_sha256=HASH_A),
        candidate_artifact=make_artifact_ref(run_id="run-2", artifact_sha256=HASH_B),
        entries=(changed, ambiguous),
        summary_counts={
            "added": 0,
            "removed": 0,
            "changed_value": 1,
            "changed_provenance": 0,
            "changed_confidence": 0,
            "unchanged": 0,
            "ambiguous_match": 1,
        },
        signed_manifest_refs=(),
    )

    assert tuple(entry.diff_kind for entry in report.entries) == (
        "changed_value",
        "ambiguous_match",
    )
    assert report.summary_counts["changed_value"] == 1
    assert report.summary_counts["ambiguous_match"] == 1

    with pytest.raises(ValidationError, match="added"):
        RunDiffEntry(
            diff_entry_id="diff-invalid-added",
            diff_kind="added",
            old_refs=(old_ref,),
            new_refs=(new_ref,),
            reason="new_fact",
        )

    with pytest.raises(ValidationError, match="summary_counts"):
        RunDiffReport(
            report_schema_version="run_diff_report.v1",
            diff_run_id="diff-invalid-summary",
            generated_at=GENERATED,
            base_artifact=make_artifact_ref(run_id="run-1", artifact_sha256=HASH_A),
            candidate_artifact=make_artifact_ref(run_id="run-2", artifact_sha256=HASH_B),
            entries=(changed,),
            summary_counts={
                "added": 0,
                "removed": 0,
                "changed_value": 0,
                "changed_provenance": 0,
                "changed_confidence": 0,
                "unchanged": 0,
                "ambiguous_match": 0,
            },
            signed_manifest_refs=(),
        )
