from __future__ import annotations

import asyncio
import hashlib

from extractor.audit import AuditStore
from extractor.chunker.token_offsets import (
    TokenOffsetError,
    TokenOffsetMap,
    build_token_offset_map,
    next_token_end_at_char_boundary,
    next_token_start_at_char_boundary,
    token_span_to_text_range,
)
from extractor.config import ChunkingConfig
from extractor.contracts import Chunk, Document


class ChunkingError(RuntimeError):
    """Raised when token-aware chunking cannot preserve source offsets."""


async def chunk_document(
    document: Document,
    config: ChunkingConfig,
    *,
    audit_store: AuditStore | None = None,
) -> tuple[Chunk, ...]:
    chunks = await asyncio.to_thread(_chunk_document_sync, document, config)
    if audit_store is not None:
        for chunk in chunks:
            await audit_store.record_chunk(chunk)
    return chunks


def _chunk_document_sync(document: Document, config: ChunkingConfig) -> tuple[Chunk, ...]:
    encoding = _load_encoding(config.tokenizer)
    tokens = encoding.encode(document.text, disallowed_special=())
    if not tokens:
        raise ChunkingError(f"Document has no tokens: {document.doc_id}")

    try:
        offsets = build_token_offset_map(document.text, encoding, tokens)

        chunks: list[Chunk] = []
        start_token = 0
        while start_token < len(offsets.tokens):
            start_token = next_token_start_at_char_boundary(start_token, offsets)
            if start_token >= len(offsets.tokens):
                break

            raw_end_token = min(start_token + config.window_tokens, len(offsets.tokens))
            end_token = next_token_end_at_char_boundary(raw_end_token, offsets)
            if end_token <= start_token:
                raise ChunkingError("Token window did not advance")

            chunk = _build_chunk(
                document=document,
                chunk_index=len(chunks),
                start_token=start_token,
                end_token=end_token,
                offsets=offsets,
            )
            chunks.append(chunk)

            if end_token >= len(offsets.tokens):
                break
            start_token = max(end_token - config.overlap_tokens, start_token + 1)
    except TokenOffsetError as exc:
        raise ChunkingError(str(exc)) from exc

    if not chunks:
        raise ChunkingError(f"Document produced no chunks: {document.doc_id}")
    return tuple(chunks)


def _load_encoding(tokenizer: str) -> object:
    try:
        import tiktoken

        return tiktoken.get_encoding(tokenizer)
    except ValueError as exc:
        raise ChunkingError(f"Unknown tokenizer: {tokenizer}") from exc
    except ImportError as exc:
        raise ChunkingError("tiktoken is required for document chunking") from exc


def _build_chunk(
    *,
    document: Document,
    chunk_index: int,
    start_token: int,
    end_token: int,
    offsets: TokenOffsetMap,
) -> Chunk:
    text_range = token_span_to_text_range(offsets, start_token, end_token)
    text = document.text[text_range.start_char : text_range.end_char]
    return Chunk(
        chunk_id=_stable_chunk_id(
            document=document,
            chunk_index=chunk_index,
            start_byte=text_range.start_byte,
            end_byte=text_range.end_byte,
            start_token=start_token,
            end_token=end_token,
        ),
        doc_id=document.doc_id,
        chunk_index=chunk_index,
        text=text,
        start_char=text_range.start_char,
        end_char=text_range.end_char,
        start_byte=text_range.start_byte,
        end_byte=text_range.end_byte,
        start_token=start_token,
        end_token=end_token,
    )


def _stable_chunk_id(
    *,
    document: Document,
    chunk_index: int,
    start_byte: int,
    end_byte: int,
    start_token: int,
    end_token: int,
) -> str:
    payload = (
        f"{document.doc_id}\0{document.text_sha256}\0{chunk_index}\0"
        f"{start_byte}\0{end_byte}\0{start_token}\0{end_token}"
    )
    return f"chunk-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:32]}"


__all__ = ["ChunkingError", "chunk_document"]
