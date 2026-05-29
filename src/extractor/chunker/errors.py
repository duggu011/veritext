class ChunkingError(RuntimeError):
    """Raised when chunking cannot preserve source offsets or boundaries."""


__all__ = ["ChunkingError"]
