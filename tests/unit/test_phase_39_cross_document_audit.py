from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import pytest

from extractor.audit import AuditIntegrityError, AuditStore
from extractor.contracts import CrossDocumentRunManifest
from tests.unit.test_phase_39_cross_document_reconciliation import (
    _reconcile_service,
    make_data_point,
    make_document,
    make_schema_metadata,
)


STARTED = datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc)
COMPLETED = datetime(2026, 5, 29, 12, 5, tzinfo=timezone.utc)


def make_cross_document_result():
    reconcile = _reconcile_service()
    first = make_data_point(
        run_id="run-a",
        doc_id="doc-a",
        data_point_id="dp-a",
        value="30 days",
        source_text="payment is due in 30 days",
        start_char=0,
    )
    second = make_data_point(
        run_id="run-b",
        doc_id="doc-b",
        data_point_id="dp-b",
        value="30 days",
        source_text="payment is due in 30 days",
        start_char=0,
    )
    return reconcile(
        cross_document_run_id="xrun-1",
        data_points=(first, second),
        documents=(make_document("doc-a"), make_document("doc-b")),
        schema_metadata_by_run_id={
            "run-a": make_schema_metadata(),
            "run-b": make_schema_metadata(),
        },
    )


def make_cross_document_manifest() -> CrossDocumentRunManifest:
    result = make_cross_document_result()
    return CrossDocumentRunManifest(
        cross_document_run_id=result.cross_document_run_id,
        audit_db_path="/tmp/audit.sqlite3",
        status="completed",
        started_at=STARTED,
        completed_at=COMPLETED,
        input_run_ids=result.input_run_ids,
        output_group_ids=tuple(group.group_id for group in result.groups),
        output_conflict_ids=tuple(conflict.conflict_id for conflict in result.conflicts),
    )


def test_audit_store_round_trips_cross_document_manifest_and_result(tmp_path: Path) -> None:
    async def run_check() -> None:
        db_path = tmp_path / "audit.sqlite3"
        manifest = make_cross_document_manifest()
        result = make_cross_document_result()

        async with AuditStore(db_path) as store:
            await store.record_cross_document_run_manifest(manifest)
            await store.record_cross_document_reconciliation_result(result)

            assert await store.get_schema_version() == "1"
            assert await store.get_cross_document_run_manifest("xrun-1") == manifest
            assert await store.list_cross_document_run_manifests() == (manifest,)
            assert await store.get_cross_document_reconciliation_result("xrun-1") == result

    asyncio.run(run_check())


def test_audit_store_rejects_duplicate_cross_document_payloads(tmp_path: Path) -> None:
    async def run_check() -> None:
        manifest = make_cross_document_manifest()
        result = make_cross_document_result()

        async with AuditStore(tmp_path / "audit.sqlite3") as store:
            await store.record_cross_document_run_manifest(manifest)
            await store.record_cross_document_reconciliation_result(result)

            with pytest.raises(AuditIntegrityError):
                await store.record_cross_document_run_manifest(manifest)
            with pytest.raises(AuditIntegrityError):
                await store.record_cross_document_reconciliation_result(result)

    asyncio.run(run_check())


def test_audit_store_rejects_orphan_cross_document_result(tmp_path: Path) -> None:
    async def run_check() -> None:
        async with AuditStore(tmp_path / "audit.sqlite3") as store:
            with pytest.raises(AuditIntegrityError):
                await store.record_cross_document_reconciliation_result(
                    make_cross_document_result()
                )

    asyncio.run(run_check())
