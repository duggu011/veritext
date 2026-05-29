import pytest

from extractor.chunker import ChunkingError
from extractor.chunker.boundaries import collect_chunk_boundaries
from extractor.contracts import Document, LayoutSpan, PageSpan, TableCellSpan, TableSpan, TextRange


HASH = "a" * 64


def text_range(start: int, end: int) -> TextRange:
    return TextRange(start_char=start, end_char=end, start_byte=start, end_byte=end)


def make_document(
    text: str,
    *,
    page_map: tuple[PageSpan, ...],
    layout_spans: tuple[LayoutSpan, ...] = (),
    table_spans: tuple[TableSpan, ...] = (),
) -> Document:
    return Document(
        doc_id="doc-1",
        source_path="/tmp/doc.txt",
        format="plain_text",
        text=text,
        source_sha256=HASH,
        text_sha256=HASH,
        source_byte_length=len(text.encode("utf-8")),
        text_byte_length=len(text.encode("utf-8")),
        page_map=page_map,
        layout_spans=layout_spans,
        table_spans=table_spans,
    )


def test_collect_chunk_boundaries_indexes_pages_layout_spans_and_tables() -> None:
    text = "Title\nFirst paragraph\nA | B\n1 | 2"
    document = make_document(
        text,
        page_map=(PageSpan(page_number=1, start_char=0, end_char=33, start_byte=0, end_byte=33),),
        layout_spans=(
            LayoutSpan(span_id="layout-heading", page_number=1, role="heading", text_range=text_range(0, 5)),
            LayoutSpan(
                span_id="layout-paragraph",
                page_number=1,
                role="paragraph",
                text_range=text_range(6, 21),
            ),
        ),
        table_spans=(
            TableSpan(
                table_id="table-1",
                page_number=1,
                text_range=text_range(22, 33),
                cells=(
                    TableCellSpan(cell_id="cell-1", text_range=text_range(22, 27), row_index=0, column_index=0),
                    TableCellSpan(cell_id="cell-2", text_range=text_range(28, 33), row_index=1, column_index=0),
                ),
            ),
        ),
    )

    boundaries = collect_chunk_boundaries(document)

    assert boundaries.page_numbers == (1,)
    assert boundaries.layout_span_ids == ("layout-heading", "layout-paragraph")
    assert boundaries.table_ids == ("table-1",)
    assert [boundary.char_offset for boundary in boundaries.boundaries] == sorted(
        boundary.char_offset for boundary in boundaries.boundaries
    )
    assert {
        (boundary.kind, boundary.char_offset, boundary.layout_span_id, boundary.layout_role)
        for boundary in boundaries.boundaries
        if boundary.layout_span_id is not None
    } == {
        ("layout_start", 0, "layout-heading", "heading"),
        ("layout_end", 5, "layout-heading", "heading"),
        ("layout_start", 6, "layout-paragraph", "paragraph"),
        ("layout_end", 21, "layout-paragraph", "paragraph"),
    }
    assert {
        (boundary.kind, boundary.char_offset, boundary.table_id)
        for boundary in boundaries.boundaries
        if boundary.table_id is not None
    } == {
        ("table_start", 22, "table-1"),
        ("table_end", 33, "table-1"),
    }


def test_collect_chunk_boundaries_rejects_page_map_gaps() -> None:
    text = "abcdefghij"
    document = make_document(
        text,
        page_map=(
            PageSpan(page_number=1, start_char=0, end_char=4, start_byte=0, end_byte=4),
            PageSpan(page_number=2, start_char=5, end_char=10, start_byte=5, end_byte=10),
        ),
    )

    with pytest.raises(ChunkingError, match="page_map must cover document text contiguously"):
        collect_chunk_boundaries(document)


def test_collect_chunk_boundaries_rejects_layout_span_outside_declared_page() -> None:
    text = "abcdefghij"
    document = make_document(
        text,
        page_map=(
            PageSpan(page_number=1, start_char=0, end_char=5, start_byte=0, end_byte=5),
            PageSpan(page_number=2, start_char=5, end_char=10, start_byte=5, end_byte=10),
        ),
        layout_spans=(
            LayoutSpan(span_id="layout-1", page_number=1, role="paragraph", text_range=text_range(6, 8)),
        ),
    )

    with pytest.raises(ChunkingError, match="layout span layout-1 must be within page 1"):
        collect_chunk_boundaries(document)


def test_collect_chunk_boundaries_rejects_table_span_outside_declared_page() -> None:
    text = "abcdefghij"
    document = make_document(
        text,
        page_map=(
            PageSpan(page_number=1, start_char=0, end_char=5, start_byte=0, end_byte=5),
            PageSpan(page_number=2, start_char=5, end_char=10, start_byte=5, end_byte=10),
        ),
        table_spans=(
            TableSpan(
                table_id="table-1",
                page_number=1,
                text_range=text_range(6, 8),
                cells=(
                    TableCellSpan(cell_id="cell-1", text_range=text_range(6, 8), row_index=0, column_index=0),
                ),
            ),
        ),
    )

    with pytest.raises(ChunkingError, match="table span table-1 must be within page 1"):
        collect_chunk_boundaries(document)
