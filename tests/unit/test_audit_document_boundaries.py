import asyncio
import json
import sqlite3
from pathlib import Path

import pytest

from extractor.audit import AuditIntegrityError, AuditStore
from extractor.contracts import (
    Document,
    DocumentMetadata,
    LayoutSpan,
    OcrConfidenceSpan,
    PageSpan,
    SourceMapSegment,
    TableCellSpan,
    TableSpan,
    TextRange,
)


def text_range(start: int, end: int) -> TextRange:
    return TextRange(start_char=start, end_char=end, start_byte=start, end_byte=end)


def source_segment(segment_id: str, start: int, end: int) -> SourceMapSegment:
    return SourceMapSegment(
        segment_id=segment_id,
        kind="source",
        text_range=text_range(start, end),
        source_start_byte=start,
        source_end_byte=end,
    )


def make_boundary_document() -> Document:
    text = "alpha\n\nbeta"
    return Document(
        doc_id="doc-boundary",
        source_path="/tmp/source.txt",
        format="plain_text",
        text=text,
        source_sha256="a" * 64,
        text_sha256="b" * 64,
        source_byte_length=len(text.encode("utf-8")),
        text_byte_length=len(text.encode("utf-8")),
        page_map=(
            PageSpan(
                page_number=1,
                start_char=0,
                end_char=len(text),
                start_byte=0,
                end_byte=len(text.encode("utf-8")),
            ),
        ),
        metadata=DocumentMetadata(source_name="source.txt", parser_name="plain-text"),
        source_map=(
            source_segment("seg-1", 0, 5),
            SourceMapSegment(
                segment_id="sep-1",
                kind="generated",
                text_range=text_range(5, 7),
            ),
            source_segment("seg-2", 7, 11),
        ),
        layout_spans=(
            LayoutSpan(
                span_id="layout-1",
                page_number=1,
                role="paragraph",
                text_range=text_range(0, 5),
            ),
        ),
        table_spans=(
            TableSpan(
                table_id="table-1",
                page_number=1,
                text_range=text_range(7, 11),
                cells=(
                    TableCellSpan(
                        cell_id="cell-1",
                        text_range=text_range(7, 11),
                        row_index=0,
                        column_index=0,
                    ),
                ),
            ),
        ),
        ocr_confidence_spans=(
            OcrConfidenceSpan(
                span_id="ocr-1",
                text_range=text_range(0, 5),
                confidence=0.75,
                engine="fixture-ocr",
            ),
        ),
    )


def test_audit_store_round_trips_document_boundary_payload(tmp_path: Path) -> None:
    db_path = tmp_path / "audit.sqlite3"

    async def run_check() -> None:
        document = make_boundary_document()
        async with AuditStore(db_path) as store:
            await store.record_document(document)
            await store.record_document(document)
            stored = await store.get_document(document.doc_id)

        assert stored == document

    asyncio.run(run_check())

    with sqlite3.connect(db_path) as connection:
        (payload_json,) = connection.execute(
            "SELECT payload_json FROM documents WHERE doc_id = ?",
            ("doc-boundary",),
        ).fetchone()
    payload = json.loads(payload_json)
    assert payload["metadata"]["parser_name"] == "plain-text"
    assert [segment["kind"] for segment in payload["source_map"]] == [
        "source",
        "generated",
        "source",
    ]
    assert payload["layout_spans"][0]["role"] == "paragraph"
    assert payload["table_spans"][0]["cells"][0]["cell_id"] == "cell-1"
    assert payload["ocr_confidence_spans"][0]["confidence"] == 0.75


def test_audit_store_rejects_same_document_id_with_conflicting_boundaries(tmp_path: Path) -> None:
    async def run_check() -> None:
        document = make_boundary_document()
        conflicting = document.model_copy(
            update={
                "metadata": DocumentMetadata(
                    source_name="source.txt",
                    parser_name="different-parser",
                )
            }
        )
        async with AuditStore(tmp_path / "audit.sqlite3") as store:
            await store.record_document(document)
            with pytest.raises(AuditIntegrityError):
                await store.record_document(conflicting)

    asyncio.run(run_check())
