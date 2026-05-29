import asyncio
import hashlib

import pytest

from extractor.chunker import ChunkingError, chunk_document
from extractor.config import ChunkingConfig
from extractor.contracts import Document, LayoutSpan, PageSpan, TableCellSpan, TableSpan, TextRange


HASH = "a" * 64


def text_range(start: int, end: int) -> TextRange:
    return TextRange(start_char=start, end_char=end, start_byte=start, end_byte=end)


def make_config(
    *,
    window_tokens: int,
    allow_oversized_atomic_chunks: bool = True,
) -> ChunkingConfig:
    return ChunkingConfig(
        tokenizer="cl100k_base",
        window_tokens=window_tokens,
        overlap_tokens=0,
        boundary_mode="layout_aware",
        allow_oversized_atomic_chunks=allow_oversized_atomic_chunks,
    )


def make_document(
    text: str,
    *,
    layout_spans: tuple[LayoutSpan, ...] = (),
    table_spans: tuple[TableSpan, ...] = (),
) -> Document:
    text_bytes = text.encode("utf-8")
    return Document(
        doc_id="doc-1",
        source_path="/tmp/doc.txt",
        format="plain_text",
        text=text,
        source_sha256=HASH,
        text_sha256=hashlib.sha256(text_bytes).hexdigest(),
        source_byte_length=len(text_bytes),
        text_byte_length=len(text_bytes),
        page_map=(
            PageSpan(
                page_number=1,
                start_char=0,
                end_char=len(text),
                start_byte=0,
                end_byte=len(text_bytes),
            ),
        ),
        layout_spans=layout_spans,
        table_spans=table_spans,
    )


def test_layout_aware_chunking_prefers_sentence_and_heading_boundaries() -> None:
    async def run_check() -> None:
        text = "Alpha beta gamma. Delta epsilon zeta.\n\nTerms\nPayment must occur promptly."
        first_paragraph_end = text.index("\n\n")
        heading_start = text.index("Terms")
        heading_end = heading_start + len("Terms")
        final_paragraph_start = text.index("Payment")
        document = make_document(
            text,
            layout_spans=(
                LayoutSpan(
                    span_id="layout-intro",
                    page_number=1,
                    role="paragraph",
                    text_range=text_range(0, first_paragraph_end),
                ),
                LayoutSpan(
                    span_id="layout-heading",
                    page_number=1,
                    role="heading",
                    text_range=text_range(heading_start, heading_end),
                ),
                LayoutSpan(
                    span_id="layout-payment",
                    page_number=1,
                    role="paragraph",
                    text_range=text_range(final_paragraph_start, len(text)),
                ),
            ),
        )

        chunks = await chunk_document(document, make_config(window_tokens=5))

        assert any(chunk.text == "Alpha beta gamma." for chunk in chunks)
        assert any(chunk.text.startswith(" Delta epsilon zeta.") for chunk in chunks)
        heading_chunk = next(chunk for chunk in chunks if "Terms" in chunk.text)
        assert heading_chunk.text.startswith("Terms")
        assert heading_chunk.chunk_kind == "section"
        assert heading_chunk.layout_span_ids[0] == "layout-heading"
        assert "".join(chunk.text for chunk in chunks) == text

    asyncio.run(run_check())


def test_layout_aware_chunking_keeps_oversized_tables_atomic() -> None:
    async def run_check() -> None:
        text = "Intro\nA B C D E F G H I J"
        table_start = text.index("A")
        document = make_document(
            text,
            layout_spans=(
                LayoutSpan(
                    span_id="layout-intro",
                    page_number=1,
                    role="paragraph",
                    text_range=text_range(0, table_start - 1),
                ),
            ),
            table_spans=(
                TableSpan(
                    table_id="table-1",
                    page_number=1,
                    text_range=text_range(table_start, len(text)),
                    cells=(
                        TableCellSpan(
                            cell_id="cell-1",
                            text_range=text_range(table_start, len(text)),
                            row_index=0,
                            column_index=0,
                        ),
                    ),
                ),
            ),
        )

        chunks = await chunk_document(document, make_config(window_tokens=3))
        table_chunk = next(chunk for chunk in chunks if chunk.table_ids == ("table-1",))

        assert table_chunk.text == text[table_start:]
        assert table_chunk.chunk_kind == "table"
        assert table_chunk.split_reason == "atomic_table_overflow"

    asyncio.run(run_check())


def test_layout_aware_chunking_can_reject_oversized_atomic_tables() -> None:
    async def run_check() -> None:
        text = "Intro\nA B C D E F G H I J"
        table_start = text.index("A")
        document = make_document(
            text,
            table_spans=(
                TableSpan(
                    table_id="table-1",
                    page_number=1,
                    text_range=text_range(table_start, len(text)),
                    cells=(
                        TableCellSpan(
                            cell_id="cell-1",
                            text_range=text_range(table_start, len(text)),
                            row_index=0,
                            column_index=0,
                        ),
                    ),
                ),
            ),
        )

        with pytest.raises(ChunkingError, match="Oversized table chunk exceeds window"):
            await chunk_document(
                document,
                make_config(window_tokens=3, allow_oversized_atomic_chunks=False),
            )

    asyncio.run(run_check())
