from __future__ import annotations


class ReconcilerError(RuntimeError):
    """Raised when reconciliation inputs or decisions cannot preserve provenance."""


class CrossDocumentReconciliationError(RuntimeError):
    """Raised when cross-document reconciliation cannot preserve audit links."""


__all__ = ["CrossDocumentReconciliationError", "ReconcilerError"]
