from __future__ import annotations

from extractor.audit.base import SQLiteAuditStore
from extractor.contracts import (
    CrossDocumentReconciliationResult,
    CrossDocumentRunManifest,
)


class CrossDocumentAuditRecords(SQLiteAuditStore):
    async def record_cross_document_run_manifest(
        self,
        manifest: CrossDocumentRunManifest,
    ) -> None:
        values = manifest.model_dump(mode="json")
        await self._insert_payload(
            "cross_document_run_manifests",
            {
                "cross_document_run_id": manifest.cross_document_run_id,
                "status": manifest.status,
                "started_at": values["started_at"],
                "completed_at": values["completed_at"],
                "payload_json": manifest.model_dump_json(),
            },
        )

    async def get_cross_document_run_manifest(
        self,
        cross_document_run_id: str,
    ) -> CrossDocumentRunManifest | None:
        return await self._fetch_payload(
            "cross_document_run_manifests",
            "cross_document_run_id",
            cross_document_run_id,
            CrossDocumentRunManifest,
        )

    async def list_cross_document_run_manifests(
        self,
    ) -> tuple[CrossDocumentRunManifest, ...]:
        return await self._list_payloads(
            "cross_document_run_manifests",
            CrossDocumentRunManifest,
            "1 = 1",
            (),
            "started_at DESC, cross_document_run_id ASC",
        )

    async def record_cross_document_reconciliation_result(
        self,
        result: CrossDocumentReconciliationResult,
    ) -> None:
        await self._insert_payload(
            "cross_document_results",
            {
                "cross_document_run_id": result.cross_document_run_id,
                "payload_json": result.model_dump_json(),
            },
        )

    async def get_cross_document_reconciliation_result(
        self,
        cross_document_run_id: str,
    ) -> CrossDocumentReconciliationResult | None:
        return await self._fetch_payload(
            "cross_document_results",
            "cross_document_run_id",
            cross_document_run_id,
            CrossDocumentReconciliationResult,
        )


__all__ = ["CrossDocumentAuditRecords"]
