from __future__ import annotations


class ExecutorError(RuntimeError):
    """Raised when executor inputs or budgets prevent auditable extraction."""


__all__ = ["ExecutorError"]
