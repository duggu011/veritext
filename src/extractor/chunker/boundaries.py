from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from extractor.chunker.errors import ChunkingError
from extractor.contracts import Document, LayoutRole, PageSpan, TextRange


ChunkBoundaryKind = Literal[
    "document_start",
    "document_end",
    "page_start",
    "page_end",
    "layout_start",
    "layout_end",
    "table_start",
    "table_end",
]

_BOUNDARY_PRIORITIES: dict[ChunkBoundaryKind, int] = {
    "document_start": 0,
    "document_end": 0,
    "page_start": 10,
    "page_end": 10,
    "layout_start": 20,
    "layout_end": 20,
    "table_start": 30,
    "table_end": 30,
}


@dataclass(frozen=True)
class ChunkBoundary:
    boundary_id: str
    kind: ChunkBoundaryKind
    char_offset: int
    byte_offset: int
    priority: int
    page_number: int | None = None
    layout_span_id: str | None = None
    layout_role: LayoutRole | None = None
    table_id: str | None = None


@dataclass(frozen=True)
class ChunkBoundarySet:
    boundaries: tuple[ChunkBoundary, ...]
    page_numbers: tuple[int, ...]
    layout_span_ids: tuple[str, ...]
    table_ids: tuple[str, ...]


def collect_chunk_boundaries(document: Document) -> ChunkBoundarySet:
    page_by_number = _validate_page_map_coverage(document)
    boundaries: list[ChunkBoundary] = [
        _boundary(
            boundary_id="document:start",
            kind="document_start",
            char_offset=0,
            byte_offset=0,
        ),
        _boundary(
            boundary_id="document:end",
            kind="document_end",
            char_offset=len(document.text),
            byte_offset=document.text_byte_length,
        ),
    ]

    for page in document.page_map:
        boundaries.append(
            _boundary(
                boundary_id=f"page:{page.page_number}:start",
                kind="page_start",
                char_offset=page.start_char,
                byte_offset=page.start_byte,
                page_number=page.page_number,
            )
        )
        boundaries.append(
            _boundary(
                boundary_id=f"page:{page.page_number}:end",
                kind="page_end",
                char_offset=page.end_char,
                byte_offset=page.end_byte,
                page_number=page.page_number,
            )
        )

    for span in document.layout_spans:
        page = page_by_number[span.page_number]
        _ensure_range_within_page(
            label=f"layout span {span.span_id}",
            text_range=span.text_range,
            page=page,
        )
        boundaries.append(
            _boundary(
                boundary_id=f"layout:{span.span_id}:start",
                kind="layout_start",
                char_offset=span.text_range.start_char,
                byte_offset=span.text_range.start_byte,
                page_number=span.page_number,
                layout_span_id=span.span_id,
                layout_role=span.role,
            )
        )
        boundaries.append(
            _boundary(
                boundary_id=f"layout:{span.span_id}:end",
                kind="layout_end",
                char_offset=span.text_range.end_char,
                byte_offset=span.text_range.end_byte,
                page_number=span.page_number,
                layout_span_id=span.span_id,
                layout_role=span.role,
            )
        )

    for table in document.table_spans:
        page = page_by_number[table.page_number]
        _ensure_range_within_page(
            label=f"table span {table.table_id}",
            text_range=table.text_range,
            page=page,
        )
        boundaries.append(
            _boundary(
                boundary_id=f"table:{table.table_id}:start",
                kind="table_start",
                char_offset=table.text_range.start_char,
                byte_offset=table.text_range.start_byte,
                page_number=table.page_number,
                table_id=table.table_id,
            )
        )
        boundaries.append(
            _boundary(
                boundary_id=f"table:{table.table_id}:end",
                kind="table_end",
                char_offset=table.text_range.end_char,
                byte_offset=table.text_range.end_byte,
                page_number=table.page_number,
                table_id=table.table_id,
            )
        )

    return ChunkBoundarySet(
        boundaries=tuple(sorted(boundaries, key=_boundary_sort_key)),
        page_numbers=tuple(page.page_number for page in document.page_map),
        layout_span_ids=tuple(span.span_id for span in document.layout_spans),
        table_ids=tuple(table.table_id for table in document.table_spans),
    )


def _validate_page_map_coverage(document: Document) -> dict[int, PageSpan]:
    previous_char_end = 0
    previous_byte_end = 0
    page_by_number: dict[int, PageSpan] = {}
    for page in document.page_map:
        if page.start_char != previous_char_end or page.start_byte != previous_byte_end:
            raise ChunkingError("page_map must cover document text contiguously")
        previous_char_end = page.end_char
        previous_byte_end = page.end_byte
        page_by_number[page.page_number] = page

    if previous_char_end != len(document.text) or previous_byte_end != document.text_byte_length:
        raise ChunkingError("page_map must cover document text contiguously")
    return page_by_number


def _ensure_range_within_page(*, label: str, text_range: TextRange, page: PageSpan) -> None:
    if (
        text_range.start_char < page.start_char
        or text_range.end_char > page.end_char
        or text_range.start_byte < page.start_byte
        or text_range.end_byte > page.end_byte
    ):
        raise ChunkingError(f"{label} must be within page {page.page_number}")


def _boundary(
    *,
    boundary_id: str,
    kind: ChunkBoundaryKind,
    char_offset: int,
    byte_offset: int,
    page_number: int | None = None,
    layout_span_id: str | None = None,
    layout_role: LayoutRole | None = None,
    table_id: str | None = None,
) -> ChunkBoundary:
    return ChunkBoundary(
        boundary_id=boundary_id,
        kind=kind,
        char_offset=char_offset,
        byte_offset=byte_offset,
        priority=_BOUNDARY_PRIORITIES[kind],
        page_number=page_number,
        layout_span_id=layout_span_id,
        layout_role=layout_role,
        table_id=table_id,
    )


def _boundary_sort_key(boundary: ChunkBoundary) -> tuple[int, int, int, str]:
    return (
        boundary.char_offset,
        boundary.byte_offset,
        boundary.priority,
        boundary.boundary_id,
    )


__all__ = [
    "ChunkBoundary",
    "ChunkBoundaryKind",
    "ChunkBoundarySet",
    "collect_chunk_boundaries",
]
