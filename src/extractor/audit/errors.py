from __future__ import annotations


class AuditStoreError(RuntimeError):
    """Base class for audit storage failures."""


class AuditSchemaError(AuditStoreError):
    """Raised when an audit database schema is incompatible."""


class AuditIntegrityError(AuditStoreError):
    """Raised when an audit write would violate identity or provenance constraints."""


class AuditNotFoundError(AuditStoreError):
    """Raised when an explicit audit update targets a missing record."""


__all__ = [
    "AuditIntegrityError",
    "AuditNotFoundError",
    "AuditSchemaError",
    "AuditStoreError",
]
