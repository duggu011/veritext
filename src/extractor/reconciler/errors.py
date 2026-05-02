from __future__ import annotations


class ReconcilerError(RuntimeError):
    """Raised when reconciliation inputs or decisions cannot preserve provenance."""


__all__ = ["ReconcilerError"]
