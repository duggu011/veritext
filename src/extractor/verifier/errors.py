from __future__ import annotations


class VerifierError(RuntimeError):
    """Raised when verifier inputs lack auditable critic provenance."""


__all__ = ["VerifierError"]
