from __future__ import annotations

from datetime import datetime, timezone

import pytest

from extractor.audit import AuditIntegrityError, AuditStore
from extractor.contracts import AuditIntegrityEvent


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
HASH_D = "d" * 64
CREATED = datetime(2026, 5, 30, 10, 0, tzinfo=timezone.utc)


def make_event(
    *,
    event_id: str = "aie-1",
    previous_chain_hash: str | None = None,
    chain_hash: str = HASH_C,
) -> AuditIntegrityEvent:
    return AuditIntegrityEvent(
        event_id=event_id,
        event_kind="report_manifest_signed",
        run_id="run-1",
        cross_document_run_id=None,
        artifact_sha256=HASH_A,
        payload_sha256=HASH_B,
        previous_chain_hash=previous_chain_hash,
        chain_hash=chain_hash,
        created_at=CREATED,
        payload_json={"signed_payload_sha256": HASH_B},
    )


def test_audit_store_records_and_reads_integrity_events(tmp_path) -> None:
    async def run_check() -> None:
        db_path = tmp_path / "audit.sqlite3"
        async with AuditStore(db_path) as store:
            first = make_event()
            second = make_event(
                event_id="aie-2",
                previous_chain_hash=HASH_C,
                chain_hash=HASH_D,
            )

            await store.record_audit_integrity_event(first)
            await store.record_audit_integrity_event(second)

            assert await store.get_audit_integrity_event("aie-1") == first
            assert await store.list_audit_integrity_events(run_id="run-1") == (
                first,
                second,
            )
            assert await store.get_latest_audit_integrity_chain_hash() == HASH_D

    import asyncio

    asyncio.run(run_check())


def test_audit_store_rejects_conflicting_integrity_event_ids(tmp_path) -> None:
    async def run_check() -> None:
        db_path = tmp_path / "audit.sqlite3"
        async with AuditStore(db_path) as store:
            await store.record_audit_integrity_event(make_event())

            with pytest.raises(AuditIntegrityError):
                await store.record_audit_integrity_event(
                    make_event(previous_chain_hash=HASH_D)
                )

    import asyncio

    asyncio.run(run_check())
