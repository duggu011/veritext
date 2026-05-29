from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Protocol

from extractor.chunker.boundaries import collect_chunk_boundaries
from extractor.chunker.errors import ChunkingError
from extractor.config import ChunkingConfig
from extractor.contracts import Document, LayoutRole


class PackingEncoding(Protocol):
    def encode(self, text: str, *, disallowed_special: tuple[()] = ()) -> list[int]: ...


@dataclass(frozen=True)
class ChunkBlock:
    start_char: int
    end_char: int
    kind: str
    layout_span_id: str | None = None
    layout_role: LayoutRole | None = None
    table_id: str | None = None


@dataclass(frozen=True)
class PackedChunk:
    start_char: int
    end_char: int
    chunk_kind: str
    layout_span_ids: tuple[str, ...]
    table_ids: tuple[str, ...]
    page_numbers: tuple[int, ...]
    split_reason: str


def pack_boundary_aware_chunks(
    document: Document,
    config: ChunkingConfig,
    encoding: PackingEncoding,
) -> tuple[PackedChunk, ...]:
    collect_chunk_boundaries(document)
    blocks = _collect_blocks(document)
    if not blocks:
        return (
            PackedChunk(
                start_char=0,
                end_char=len(document.text),
                chunk_kind="document",
                layout_span_ids=(),
                table_ids=(),
                page_numbers=_page_numbers_for_range(document, 0, len(document.text)),
                split_reason="boundary",
            ),
        )

    chunks: list[PackedChunk] = []
    current: list[ChunkBlock] = []

    def flush_current() -> None:
        if current:
            chunks.append(_pack_blocks(document, current, split_reason="boundary"))
            current.clear()

    for block in blocks:
        if block.kind == "table":
            flush_current()
            chunks.append(_pack_table_block(document, config, encoding, block))
            continue

        if block.kind == "section":
            flush_current()

        if _token_count(document, encoding, block.start_char, block.end_char) > config.window_tokens:
            flush_current()
            chunks.extend(_split_oversized_text_block(document, config, encoding, block))
            continue

        if current:
            candidate_start = current[0].start_char
            if _token_count(document, encoding, candidate_start, block.end_char) > config.window_tokens:
                flush_current()

        current.append(block)

    flush_current()
    return tuple(chunks)


def _collect_blocks(document: Document) -> tuple[ChunkBlock, ...]:
    blocks: list[ChunkBlock] = []
    table_ranges = tuple((table.text_range.start_char, table.text_range.end_char) for table in document.table_spans)

    for table in document.table_spans:
        blocks.append(
            ChunkBlock(
                start_char=table.text_range.start_char,
                end_char=table.text_range.end_char,
                kind="table",
                table_id=table.table_id,
            )
        )

    for span in document.layout_spans:
        if span.role not in {"heading", "paragraph", "list_item"}:
            continue
        if any(
            span.text_range.start_char >= table_start and span.text_range.end_char <= table_end
            for table_start, table_end in table_ranges
        ):
            continue
        blocks.append(
            ChunkBlock(
                start_char=span.text_range.start_char,
                end_char=span.text_range.end_char,
                kind="section" if span.role == "heading" else span.role,
                layout_span_id=span.span_id,
                layout_role=span.role,
            )
        )

    blocks.sort(key=lambda block: (block.start_char, block.end_char, block.kind))
    return _with_gap_blocks(document, tuple(blocks))


def _with_gap_blocks(document: Document, blocks: tuple[ChunkBlock, ...]) -> tuple[ChunkBlock, ...]:
    filled: list[ChunkBlock] = []
    cursor = 0
    for block in blocks:
        if block.start_char < cursor:
            raise ChunkingError("layout-aware blocks must be ordered and non-overlapping")
        if block.start_char > cursor:
            gap_text = document.text[cursor : block.start_char]
            if gap_text.isspace() and filled:
                filled[-1] = replace(filled[-1], end_char=block.start_char)
            else:
                filled.append(ChunkBlock(start_char=cursor, end_char=block.start_char, kind="mixed"))
        filled.append(block)
        cursor = block.end_char

    if cursor < len(document.text):
        filled.append(ChunkBlock(start_char=cursor, end_char=len(document.text), kind="mixed"))
    return tuple(block for block in filled if block.end_char > block.start_char)


def _pack_table_block(
    document: Document,
    config: ChunkingConfig,
    encoding: PackingEncoding,
    block: ChunkBlock,
) -> PackedChunk:
    split_reason = "boundary"
    if _token_count(document, encoding, block.start_char, block.end_char) > config.window_tokens:
        if not config.allow_oversized_atomic_chunks:
            raise ChunkingError("Oversized table chunk exceeds window")
        split_reason = "atomic_table_overflow"

    return PackedChunk(
        start_char=block.start_char,
        end_char=block.end_char,
        chunk_kind="table",
        layout_span_ids=(),
        table_ids=(block.table_id,) if block.table_id is not None else (),
        page_numbers=_page_numbers_for_range(document, block.start_char, block.end_char),
        split_reason=split_reason,
    )


def _pack_blocks(
    document: Document,
    blocks: list[ChunkBlock],
    *,
    split_reason: str,
) -> PackedChunk:
    layout_span_ids = tuple(block.layout_span_id for block in blocks if block.layout_span_id is not None)
    table_ids = tuple(block.table_id for block in blocks if block.table_id is not None)
    kinds = {block.kind for block in blocks if block.kind != "mixed"}
    if "section" in kinds:
        chunk_kind = "section"
    elif kinds == {"paragraph"}:
        chunk_kind = "paragraph"
    elif kinds == {"list_item"}:
        chunk_kind = "list_item"
    elif kinds == {"table"}:
        chunk_kind = "table"
    else:
        chunk_kind = "mixed"

    return PackedChunk(
        start_char=blocks[0].start_char,
        end_char=blocks[-1].end_char,
        chunk_kind=chunk_kind,
        layout_span_ids=layout_span_ids,
        table_ids=table_ids,
        page_numbers=_page_numbers_for_range(document, blocks[0].start_char, blocks[-1].end_char),
        split_reason=split_reason,
    )


def _split_oversized_text_block(
    document: Document,
    config: ChunkingConfig,
    encoding: PackingEncoding,
    block: ChunkBlock,
) -> tuple[PackedChunk, ...]:
    text = document.text[block.start_char : block.end_char]
    sentence_ends = _sentence_end_offsets(text)
    if sentence_ends == (len(text),):
        return _split_by_character_window(document, config, encoding, block, "oversized_sentence")

    chunks: list[PackedChunk] = []
    current_start = 0
    current_end = 0
    for sentence_end in sentence_ends:
        absolute_start = block.start_char + current_start
        absolute_sentence_end = block.start_char + sentence_end
        sentence_tokens = _token_count(document, encoding, block.start_char + current_end, absolute_sentence_end)
        if sentence_tokens > config.window_tokens:
            if current_end > current_start:
                chunks.append(_pack_block_slice(document, block, current_start, current_end, "boundary"))
            oversized_block = ChunkBlock(
                start_char=block.start_char + current_end,
                end_char=absolute_sentence_end,
                kind=block.kind,
                layout_span_id=block.layout_span_id,
                layout_role=block.layout_role,
            )
            chunks.extend(
                _split_by_character_window(document, config, encoding, oversized_block, "oversized_sentence")
            )
            current_start = sentence_end
            current_end = sentence_end
            continue

        if _token_count(document, encoding, absolute_start, absolute_sentence_end) > config.window_tokens:
            if current_end > current_start:
                chunks.append(_pack_block_slice(document, block, current_start, current_end, "boundary"))
            current_start = current_end
        current_end = sentence_end

    if current_end > current_start:
        chunks.append(_pack_block_slice(document, block, current_start, current_end, "boundary"))
    return tuple(chunks)


def _split_by_character_window(
    document: Document,
    config: ChunkingConfig,
    encoding: PackingEncoding,
    block: ChunkBlock,
    split_reason: str,
) -> tuple[PackedChunk, ...]:
    chunks: list[PackedChunk] = []
    start = block.start_char
    while start < block.end_char:
        end = start + 1
        best_end = end
        while end <= block.end_char:
            if _token_count(document, encoding, start, end) > config.window_tokens:
                break
            best_end = end
            end += 1
        if best_end <= start:
            raise ChunkingError("Token window did not advance")
        chunks.append(
            _pack_block_slice(
                document,
                block,
                start - block.start_char,
                best_end - block.start_char,
                split_reason,
            )
        )
        start = best_end
    return tuple(chunks)


def _pack_block_slice(
    document: Document,
    block: ChunkBlock,
    relative_start: int,
    relative_end: int,
    split_reason: str,
) -> PackedChunk:
    start_char = block.start_char + relative_start
    end_char = block.start_char + relative_end
    return PackedChunk(
        start_char=start_char,
        end_char=end_char,
        chunk_kind="overflow" if split_reason.startswith("oversized") else block.kind,
        layout_span_ids=(block.layout_span_id,) if block.layout_span_id is not None else (),
        table_ids=(block.table_id,) if block.table_id is not None else (),
        page_numbers=_page_numbers_for_range(document, start_char, end_char),
        split_reason=split_reason,
    )


def _sentence_end_offsets(text: str) -> tuple[int, ...]:
    offsets = tuple(match.end() for match in re.finditer(r"[.!?](?=\s|$)", text))
    if not offsets or offsets[-1] != len(text):
        offsets = (*offsets, len(text))
    return offsets


def _token_count(
    document: Document,
    encoding: PackingEncoding,
    start_char: int,
    end_char: int,
) -> int:
    return len(encoding.encode(document.text[start_char:end_char], disallowed_special=()))


def _page_numbers_for_range(document: Document, start_char: int, end_char: int) -> tuple[int, ...]:
    return tuple(
        page.page_number
        for page in document.page_map
        if start_char < page.end_char and end_char > page.start_char
    )


__all__ = ["PackedChunk", "pack_boundary_aware_chunks"]
