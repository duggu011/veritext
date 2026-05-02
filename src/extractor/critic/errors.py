from __future__ import annotations


class CriticError(RuntimeError):
    """Raised when critic inputs cannot be reviewed without violating provenance."""


__all__ = ["CriticError"]
