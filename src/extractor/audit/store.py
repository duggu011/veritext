from __future__ import annotations

from pathlib import Path

from extractor.audit.base import UsageSummary
from extractor.audit.core_records import CoreAuditRecords
from extractor.audit.cross_document_records import CrossDocumentAuditRecords
from extractor.audit.errors import (
    AuditIntegrityError,
    AuditNotFoundError,
    AuditSchemaError,
    AuditStoreError,
)
from extractor.audit.review_records import ReviewAuditRecords
from extractor.audit.schema import SCHEMA_SQL, SCHEMA_VERSION


class AuditStore(CoreAuditRecords, ReviewAuditRecords, CrossDocumentAuditRecords):
    """SQLite audit store preserving the public audit persistence interface."""


async def open_audit_store(database_path: str | Path) -> AuditStore:
    store = AuditStore(database_path)
    await store.connect()
    return store


__all__ = [
    "AuditIntegrityError",
    "AuditNotFoundError",
    "AuditSchemaError",
    "AuditStore",
    "AuditStoreError",
    "UsageSummary",
    "open_audit_store",
]
