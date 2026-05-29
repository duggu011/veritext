from __future__ import annotations

from extractor.audit.base import SQLiteAuditStore
from extractor.contracts import AuditIntegrityEvent


class IntegrityAuditRecords(SQLiteAuditStore):
    async def record_audit_integrity_event(self, event: AuditIntegrityEvent) -> None:
        values = event.model_dump(mode="json")
        await self._insert_payload(
            "audit_integrity_events",
            {
                "event_id": event.event_id,
                "event_kind": event.event_kind,
                "run_id": event.run_id,
                "cross_document_run_id": event.cross_document_run_id,
                "artifact_sha256": event.artifact_sha256,
                "payload_sha256": event.payload_sha256,
                "previous_chain_hash": event.previous_chain_hash,
                "chain_hash": event.chain_hash,
                "created_at": values["created_at"],
                "payload_json": event.model_dump_json(),
            },
        )

    async def get_audit_integrity_event(
        self,
        event_id: str,
    ) -> AuditIntegrityEvent | None:
        return await self._fetch_payload(
            "audit_integrity_events",
            "event_id",
            event_id,
            AuditIntegrityEvent,
        )

    async def list_audit_integrity_events(
        self,
        *,
        run_id: str | None = None,
        cross_document_run_id: str | None = None,
    ) -> tuple[AuditIntegrityEvent, ...]:
        if run_id is not None:
            return await self._list_payloads(
                "audit_integrity_events",
                AuditIntegrityEvent,
                "run_id = ?",
                (run_id,),
                "created_at ASC, event_id ASC",
            )
        if cross_document_run_id is not None:
            return await self._list_payloads(
                "audit_integrity_events",
                AuditIntegrityEvent,
                "cross_document_run_id = ?",
                (cross_document_run_id,),
                "created_at ASC, event_id ASC",
            )
        return await self._list_payloads(
            "audit_integrity_events",
            AuditIntegrityEvent,
            "1 = 1",
            (),
            "created_at ASC, event_id ASC",
        )

    async def get_latest_audit_integrity_chain_hash(self) -> str | None:
        row = await self._fetch_one(
            "SELECT chain_hash FROM audit_integrity_events "
            "ORDER BY created_at DESC, event_id DESC LIMIT 1",
            (),
        )
        if row is None:
            return None
        return str(row["chain_hash"])


__all__ = ["IntegrityAuditRecords"]
