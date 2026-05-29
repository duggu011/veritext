"""Token-aware document chunking."""

from extractor.chunker.errors import ChunkingError
from extractor.chunker.tokenizer import chunk_document

__all__ = ["ChunkingError", "chunk_document"]
