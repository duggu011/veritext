from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Sequence

from extractor.audit import AuditStore
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

    token_starts, token_ends = _token_byte_offsets(document.text, encoding, tokens)
    byte_to_char = _byte_to_char_boundaries(document.text)

    chunks: list[Chunk] = []
    start_token = 0
    while start_token < len(tokens):
        start_token = _next_token_start_at_char_boundary(start_token, token_starts, byte_to_char)
        if start_token >= len(tokens):
            break

        raw_end_token = min(start_token + config.window_tokens, len(tokens))
        end_token = _next_token_end_at_char_boundary(raw_end_token, token_ends, byte_to_char)
        if end_token <= start_token:
            raise ChunkingError("Token window did not advance")

        chunk = _build_chunk(
            document=document,
            chunk_index=len(chunks),
            start_token=start_token,
            end_token=end_token,
            token_starts=token_starts,
            token_ends=token_ends,
            byte_to_char=byte_to_char,
        )
        chunks.append(chunk)

        if end_token >= len(tokens):
            break
        start_token = max(end_token - config.overlap_tokens, start_token + 1)

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


def _token_byte_offsets(
    text: str,
    encoding: object,
    tokens: Sequence[int],
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    starts: list[int] = []
    ends: list[int] = []
    cursor = 0
    pieces: list[bytes] = []
    for token in tokens:
        piece = encoding.decode_single_token_bytes(token)
        starts.append(cursor)
        cursor += len(piece)
        ends.append(cursor)
        pieces.append(piece)

    text_bytes = text.encode("utf-8")
    if b"".join(pieces) != text_bytes:
        raise ChunkingError("Tokenizer byte reconstruction did not match document text")
    return tuple(starts), tuple(ends)


def _byte_to_char_boundaries(text: str) -> dict[int, int]:
    boundaries = {0: 0}
    cursor = 0
    for char_index, character in enumerate(text, start=1):
        cursor += len(character.encode("utf-8"))
        boundaries[cursor] = char_index
    return boundaries


def _next_token_start_at_char_boundary(
    token_index: int,
    token_starts: Sequence[int],
    byte_to_char: dict[int, int],
) -> int:
    while token_index < len(token_starts) and token_starts[token_index] not in byte_to_char:
        token_index += 1
    return token_index


def _next_token_end_at_char_boundary(
    token_index: int,
    token_ends: Sequence[int],
    byte_to_char: dict[int, int],
) -> int:
    while token_index < len(token_ends) and token_ends[token_index - 1] not in byte_to_char:
        token_index += 1
    if token_index == len(token_ends) and token_ends[token_index - 1] not in byte_to_char:
        raise ChunkingError("Final token boundary does not align with UTF-8 text")
    return token_index


def _build_chunk(
    *,
    document: Document,
    chunk_index: int,
    start_token: int,
    end_token: int,
    token_starts: Sequence[int],
    token_ends: Sequence[int],
    byte_to_char: dict[int, int],
) -> Chunk:
    start_byte = token_starts[start_token]
    end_byte = token_ends[end_token - 1]
    start_char = byte_to_char[start_byte]
    end_char = byte_to_char[end_byte]
    text = document.text[start_char:end_char]
    return Chunk(
        chunk_id=_stable_chunk_id(
            document=document,
            chunk_index=chunk_index,
            start_byte=start_byte,
            end_byte=end_byte,
            start_token=start_token,
            end_token=end_token,
        ),
        doc_id=document.doc_id,
        chunk_index=chunk_index,
        text=text,
        start_char=start_char,
        end_char=end_char,
        start_byte=start_byte,
        end_byte=end_byte,
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
