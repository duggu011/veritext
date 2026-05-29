from __future__ import annotations

import importlib

import pytest

from tests.unit.test_phase_39_cross_document_reconciliation import (
    _reconcile_service,
    make_data_point,
    make_document,
    make_manifest,
    make_schema_metadata,
    make_source_span,
)


def test_cross_document_reconciliation_rejects_duplicate_data_point_ids() -> None:
    reconcile = _reconcile_service()
    first = make_data_point(
        run_id="run-a",
        doc_id="doc-a",
        data_point_id="dp-duplicate",
        value="30 days",
        source_text="payment is due in 30 days",
        start_char=0,
    )
    duplicate = first.model_copy(
        update={
            "run_id": "run-b",
            "doc_id": "doc-b",
            "source_span": make_source_span(
                doc_id="doc-b",
                chunk_id="chunk-b",
                text="payment is due in 30 days",
                start_char=0,
            ),
        }
    )

    error_type = getattr(
        importlib.import_module("extractor.reconciler.cross_document"),
        "CrossDocumentReconciliationError",
    )
    with pytest.raises(error_type, match="duplicate data_point_id"):
        reconcile(
            cross_document_run_id="xrun-duplicate",
            data_points=(first, duplicate),
            documents=(make_document("doc-a"), make_document("doc-b")),
            schema_metadata_by_run_id={
                "run-a": make_schema_metadata(),
                "run-b": make_schema_metadata(),
            },
        )


def test_cross_document_reconciliation_skips_missing_document_or_schema_inputs() -> None:
    reconcile = _reconcile_service()
    valid = make_data_point(
        run_id="run-a",
        doc_id="doc-a",
        data_point_id="dp-valid",
        value="30 days",
        source_text="payment is due in 30 days",
        start_char=0,
    )
    missing_document = make_data_point(
        run_id="run-b",
        doc_id="doc-missing",
        data_point_id="dp-missing-doc",
        value="30 days",
        source_text="payment is due in 30 days",
        start_char=0,
    )
    missing_schema = make_data_point(
        run_id="run-missing-schema",
        doc_id="doc-schema",
        data_point_id="dp-missing-schema",
        value="30 days",
        source_text="payment is due in 30 days",
        start_char=0,
    )

    result = reconcile(
        cross_document_run_id="xrun-skip-missing",
        data_points=(valid, missing_document, missing_schema),
        documents=(make_document("doc-a"), make_document("doc-schema")),
        schema_metadata_by_run_id={"run-a": make_schema_metadata()},
    )

    assert len(result.groups) == 1
    assert tuple(group.sources[0].data_point_id for group in result.groups) == ("dp-valid",)
    assert {(item.input_id, item.input_kind, item.reason) for item in result.skipped_inputs} == {
        ("dp-missing-doc", "data_point", "missing_document"),
        ("dp-missing-schema", "data_point", "missing_schema_metadata"),
    }


def test_cross_document_reconciliation_accounts_for_incomplete_runs_and_missing_outputs() -> None:
    reconcile = _reconcile_service()
    completed = make_data_point(
        run_id="run-a",
        doc_id="doc-a",
        data_point_id="dp-a",
        value="30 days",
        source_text="payment is due in 30 days",
        start_char=0,
    )
    running = make_data_point(
        run_id="run-running",
        doc_id="doc-running",
        data_point_id="dp-running",
        value="30 days",
        source_text="payment is due in 30 days",
        start_char=0,
    )

    result = reconcile(
        cross_document_run_id="xrun-manifests",
        data_points=(completed, running),
        documents=(make_document("doc-a"), make_document("doc-running")),
        schema_metadata_by_run_id={
            "run-a": make_schema_metadata(),
            "run-running": make_schema_metadata(),
            "run-missing-output": make_schema_metadata(),
        },
        run_manifests=(
            make_manifest(run_id="run-a", doc_id="doc-a", output_data_point_ids=("dp-a",)),
            make_manifest(
                run_id="run-running",
                doc_id="doc-running",
                status="running",
                output_data_point_ids=("dp-running",),
            ),
            make_manifest(
                run_id="run-missing-output",
                doc_id="doc-missing-output",
                output_data_point_ids=("dp-missing",),
            ),
        ),
    )

    assert len(result.groups) == 1
    assert result.groups[0].sources[0].data_point_id == "dp-a"
    assert {(item.input_id, item.input_kind, item.reason) for item in result.skipped_inputs} == {
        ("run-running", "run", "run_not_completed"),
        ("dp-missing", "data_point", "missing_data_point"),
    }
