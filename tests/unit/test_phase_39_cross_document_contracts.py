from __future__ import annotations

import importlib
from datetime import datetime, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from extractor.contracts import CanonicalValueKey, DataPoint, SourceSpan


HASH_A = "a" * 64
HASH_B = "b" * 64
STARTED = datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc)
COMPLETED = datetime(2026, 5, 29, 12, 5, tzinfo=timezone.utc)


def _contract(name: str) -> Any:
    contracts = importlib.import_module("extractor.contracts")
    value = getattr(contracts, name, None)
    assert value is not None, f"{name} must be exported from extractor.contracts"
    return value


def make_source_span(
    *,
    doc_id: str = "doc-a",
    chunk_id: str = "chunk-a",
    text: str = "payment is due in 30 days",
    start_char: int = 0,
) -> SourceSpan:
    return SourceSpan(
        doc_id=doc_id,
        chunk_id=chunk_id,
        start_char=start_char,
        end_char=start_char + len(text),
        start_byte=start_char,
        end_byte=start_char + len(text.encode("utf-8")),
        text=text,
    )


def make_source_ref(
    *,
    run_id: str = "run-a",
    doc_id: str = "doc-a",
    data_point_id: str = "dp-a",
    value: str = "30 days",
    value_canonical: str = "30 days",
    source_sha256: str = HASH_A,
    text_sha256: str = HASH_B,
) -> Any:
    CrossDocumentSourceRef = _contract("CrossDocumentSourceRef")
    source_span = make_source_span(doc_id=doc_id, chunk_id=f"chunk-{doc_id[-1]}")
    return CrossDocumentSourceRef(
        run_id=run_id,
        doc_id=doc_id,
        data_point_id=data_point_id,
        source_span=source_span,
        supporting_source_spans=(source_span,),
        source_sha256=source_sha256,
        text_sha256=text_sha256,
        value=value,
        value_verbatim=value,
        value_canonical=value_canonical,
        value_kind="duration",
        normalization_status="canonicalized",
        normalization_policy_id="duration-key",
        normalization_policy_version="2026-05-29",
    )


def make_fact_key(value: str = "30 days") -> Any:
    CrossDocumentFactKey = _contract("CrossDocumentFactKey")
    return CrossDocumentFactKey(
        schema_id="schema:payment",
        schema_hash=HASH_A,
        category="PaymentTerm",
        field_name="payment_due",
        canonical_key=CanonicalValueKey(
            kind="duration",
            key=value,
            source="value_canonical",
            policy_id="duration-key",
            policy_version="2026-05-29",
        ),
        policy_id="cross-document-default",
        policy_version="2026-05-29",
    )


def make_fact_group(
    *,
    group_id: str = "xdg-30-days",
    value: str = "30 days",
) -> Any:
    CrossDocumentFactGroup = _contract("CrossDocumentFactGroup")
    return CrossDocumentFactGroup(
        group_id=group_id,
        key=make_fact_key(value),
        sources=(
            make_source_ref(
                run_id="run-a",
                doc_id="doc-a",
                data_point_id=f"{group_id}-a",
                value=value,
                value_canonical=value,
            ),
            make_source_ref(
                run_id="run-b",
                doc_id="doc-b",
                data_point_id=f"{group_id}-b",
                value=value,
                value_canonical=value,
            ),
        ),
        document_count=2,
        conflict_status="none",
        conflict_ids=(),
    )


def test_cross_document_source_ref_preserves_document_provenance() -> None:
    CrossDocumentSourceRef = _contract("CrossDocumentSourceRef")

    source_ref = make_source_ref()

    assert source_ref.run_id == "run-a"
    assert source_ref.doc_id == "doc-a"
    assert source_ref.data_point_id == "dp-a"
    assert source_ref.source_span.doc_id == "doc-a"
    assert source_ref.supporting_source_spans == (source_ref.source_span,)
    assert source_ref.source_sha256 == HASH_A
    assert source_ref.text_sha256 == HASH_B
    assert source_ref.value_canonical == "30 days"
    assert source_ref.normalization_status == "canonicalized"

    with pytest.raises(ValidationError, match="source_span doc_id"):
        CrossDocumentSourceRef(
            run_id="run-a",
            doc_id="doc-a",
            data_point_id="dp-a",
            source_span=make_source_span(doc_id="doc-other"),
            supporting_source_spans=(),
            source_sha256=HASH_A,
            text_sha256=HASH_B,
            value="30 days",
            value_verbatim="30 days",
            value_canonical="30 days",
            value_kind="duration",
            normalization_status="canonicalized",
            normalization_policy_id="duration-key",
            normalization_policy_version="2026-05-29",
        )


def test_cross_document_fact_key_and_group_are_strict_and_source_separated() -> None:
    CrossDocumentFactGroup = _contract("CrossDocumentFactGroup")

    key = make_fact_key()
    group = make_fact_group()

    assert key.schema_id == "schema:payment"
    assert key.category == "PaymentTerm"
    assert key.field_name == "payment_due"
    assert key.canonical_key.key == "30 days"
    assert group.key == key
    assert tuple(ref.doc_id for ref in group.sources) == ("doc-a", "doc-b")
    assert group.document_count == 2
    assert group.conflict_status == "none"

    with pytest.raises(ValidationError, match="document_count"):
        CrossDocumentFactGroup(
            group_id="xdg-invalid-count",
            key=key,
            sources=group.sources,
            document_count=1,
            conflict_status="none",
            conflict_ids=(),
        )


def test_cross_document_conflict_and_result_account_for_groups_and_inputs() -> None:
    CrossDocumentConflict = _contract("CrossDocumentConflict")
    CrossDocumentReconciliationResult = _contract("CrossDocumentReconciliationResult")

    thirty_day_group = make_fact_group(group_id="xdg-30-days", value="30 days")
    forty_five_day_group = make_fact_group(group_id="xdg-45-days", value="45 days")
    conflict = CrossDocumentConflict(
        conflict_id="xdc-payment-due",
        category="PaymentTerm",
        field_name="payment_due",
        conflicting_group_ids=("xdg-30-days", "xdg-45-days"),
        reason="same_field_distinct_canonical_values",
        doc_ids=("doc-a", "doc-b"),
        canonical_key_identities=(
            ("duration", "30 days", "value_canonical", "duration-key", "2026-05-29"),
            ("duration", "45 days", "value_canonical", "duration-key", "2026-05-29"),
        ),
    )
    result = CrossDocumentReconciliationResult(
        cross_document_run_id="xrun-1",
        input_run_ids=("run-a", "run-b"),
        input_doc_ids=("doc-a", "doc-b"),
        groups=(thirty_day_group, forty_five_day_group),
        conflicts=(conflict,),
        skipped_inputs=(),
    )

    assert result.cross_document_run_id == "xrun-1"
    assert result.groups == (thirty_day_group, forty_five_day_group)
    assert result.conflicts == (conflict,)
    assert result.skipped_inputs == ()

    with pytest.raises(ValidationError, match="input_run_ids"):
        CrossDocumentReconciliationResult(
            cross_document_run_id="xrun-duplicate",
            input_run_ids=("run-a", "run-a"),
            input_doc_ids=("doc-a", "doc-b"),
            groups=(thirty_day_group,),
            conflicts=(),
            skipped_inputs=(),
        )


def test_cross_document_run_manifest_tracks_inputs_outputs_and_completion() -> None:
    CrossDocumentRunManifest = _contract("CrossDocumentRunManifest")

    manifest = CrossDocumentRunManifest(
        cross_document_run_id="xrun-1",
        audit_db_path="/tmp/audit.sqlite",
        status="completed",
        started_at=STARTED,
        completed_at=COMPLETED,
        input_run_ids=("run-a", "run-b"),
        output_group_ids=("xdg-30-days",),
        output_conflict_ids=("xdc-payment-due",),
    )

    assert manifest.cross_document_run_id == "xrun-1"
    assert manifest.input_run_ids == ("run-a", "run-b")
    assert manifest.output_group_ids == ("xdg-30-days",)
    assert manifest.output_conflict_ids == ("xdc-payment-due",)

    with pytest.raises(ValidationError, match="completed"):
        CrossDocumentRunManifest(
            cross_document_run_id="xrun-running",
            audit_db_path="/tmp/audit.sqlite",
            status="completed",
            started_at=STARTED,
            completed_at=None,
            input_run_ids=("run-a",),
            output_group_ids=(),
            output_conflict_ids=(),
        )


def test_legacy_single_document_data_point_payload_remains_readable() -> None:
    payload = {
        "data_point_id": "dp-legacy",
        "run_id": "run-legacy",
        "doc_id": "doc-a",
        "category": "PaymentTerm",
        "field_name": "payment_due",
        "value": "30 days",
        "source_span": make_source_span(doc_id="doc-a").model_dump(),
        "confidence": 0.91,
        "contributing_candidate_ids": ("candidate-a",),
        "critic_report_ids": ("critic-a",),
        "verifier_report_ids": ("verifier-a",),
        "reconciliation_decision_id": "decision-a",
    }

    data_point = DataPoint.model_validate(payload)

    assert data_point.doc_id == "doc-a"
    assert data_point.supporting_source_spans == ()
    assert data_point.conflict_status == "none"
    assert data_point.value_kind == "text"
