from __future__ import annotations

import asyncio
import hashlib

from extractor.audit import AuditStore
from extractor.chunker.errors import ChunkingError
from extractor.chunker.token_offsets import (
    TokenOffsetError,
    TokenOffsetMap,
    build_token_offset_map,
    next_token_end_at_char_boundary,
    next_token_start_at_char_boundary,
    token_span_to_text_range,
)
from extractor.chunker.packing import PackedChunk, pack_boundary_aware_chunks
from extractor.config import ChunkingConfig
from extractor.contracts import Chunk, Document


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

    if config.boundary_mode == "layout_aware":
        return _chunk_document_layout_aware(document, config, encoding)

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


def _chunk_document_layout_aware(
    document: Document,
    config: ChunkingConfig,
    encoding: object,
) -> tuple[Chunk, ...]:
    packed_chunks = pack_boundary_aware_chunks(document, config, encoding)
    chunks = tuple(
        _build_chunk_from_packed(
            document=document,
            chunk_index=chunk_index,
            packed_chunk=packed_chunk,
            encoding=encoding,
        )
        for chunk_index, packed_chunk in enumerate(packed_chunks)
    )
    if not chunks:
        raise ChunkingError(f"Document produced no chunks: {document.doc_id}")
    return _attach_layout_hierarchy(chunks)


def _attach_layout_hierarchy(chunks: tuple[Chunk, ...]) -> tuple[Chunk, ...]:
    section_path: tuple[str, ...] = ()
    section_chunk_id: str | None = None
    updated_chunks: list[Chunk] = []

    for chunk in chunks:
        updates: dict[str, object] = {}
        if chunk.chunk_kind == "section":
            section_label = _first_content_line(chunk.text)
            if section_label is not None:
                section_path = (section_label,)
                section_chunk_id = chunk.chunk_id
                updates["section_path"] = section_path
        elif section_path and section_chunk_id is not None:
            updates["section_path"] = section_path
            updates["parent_chunk_id"] = section_chunk_id
            updates["depends_on_chunk_ids"] = _prepend_unique_dependency(
                section_chunk_id,
                chunk.depends_on_chunk_ids,
            )

        updated_chunks.append(chunk.model_copy(update=updates) if updates else chunk)
    return tuple(updated_chunks)


def _first_content_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _prepend_unique_dependency(chunk_id: str, dependencies: tuple[str, ...]) -> tuple[str, ...]:
    return (chunk_id, *(dependency for dependency in dependencies if dependency != chunk_id))


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


def _build_chunk_from_packed(
    *,
    document: Document,
    chunk_index: int,
    packed_chunk: PackedChunk,
    encoding: object,
) -> Chunk:
    text = document.text[packed_chunk.start_char : packed_chunk.end_char]
    start_byte = len(document.text[: packed_chunk.start_char].encode("utf-8"))
    end_byte = len(document.text[: packed_chunk.end_char].encode("utf-8"))
    start_token = len(encoding.encode(document.text[: packed_chunk.start_char], disallowed_special=()))
    end_token = len(encoding.encode(document.text[: packed_chunk.end_char], disallowed_special=()))
    if end_token <= start_token:
        raise ChunkingError("Token window did not advance")

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
        start_char=packed_chunk.start_char,
        end_char=packed_chunk.end_char,
        start_byte=start_byte,
        end_byte=end_byte,
        start_token=start_token,
        end_token=end_token,
        chunk_kind=packed_chunk.chunk_kind,
        layout_span_ids=packed_chunk.layout_span_ids,
        table_ids=packed_chunk.table_ids,
        page_numbers=packed_chunk.page_numbers,
        split_reason=packed_chunk.split_reason,
        tokenizer_policy="tiktoken",
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
