from __future__ import annotations


class OrchestratorError(RuntimeError):
    """Raised when a full extraction run cannot be orchestrated safely."""


__all__ = ["OrchestratorError"]
