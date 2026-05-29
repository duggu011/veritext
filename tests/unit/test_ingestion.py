import asyncio
import hashlib
import sys
from pathlib import Path
from types import ModuleType

import pytest

from extractor.audit import AuditStore
from extractor.ingestion import (
    EmptyDocumentError,
    IngestionError,
    UnsupportedDocumentFormatError,
    detect_document_format,
    ingest_document,
)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_ingest_plain_text_preserves_hashes_offsets_and_stable_id(tmp_path: Path) -> None:
    async def run_check() -> None:
        source = tmp_path / "sample.txt"
        text = "alpha\nécho"
        source.write_text(text, encoding="utf-8")
        source_bytes = text.encode("utf-8")

        document = await ingest_document(source)
        second_document = await ingest_document(source)

        assert document == second_document
        assert document.doc_id == f"doc-{sha256_hex(source_bytes)[:32]}"
        assert document.source_path == str(source.resolve())
        assert document.format == "plain_text"
        assert document.text == text
        assert document.source_sha256 == sha256_hex(source_bytes)
        assert document.text_sha256 == sha256_hex(source_bytes)
        assert document.source_byte_length == len(source_bytes)
        assert document.text_byte_length == len(source_bytes)
        assert len(document.page_map) == 1
        assert document.page_map[0].page_number == 1
        assert document.page_map[0].start_char == 0
        assert document.page_map[0].end_char == len(text)
        assert document.page_map[0].start_byte == 0
        assert document.page_map[0].end_byte == len(source_bytes)
        assert len(document.source_map) == 1
        assert document.source_map[0].segment_id == "source:0"
        assert document.source_map[0].kind == "source"
        assert document.source_map[0].text_range.start_char == 0
        assert document.source_map[0].text_range.end_char == len(text)
        assert document.source_map[0].text_range.start_byte == 0
        assert document.source_map[0].text_range.end_byte == len(source_bytes)
        assert document.source_map[0].source_start_byte == 0
        assert document.source_map[0].source_end_byte == len(source_bytes)
        assert document.source_map[0].source_start_char == 0
        assert document.source_map[0].source_end_char == len(text)

    asyncio.run(run_check())


def test_ingest_markdown_detects_format_and_records_audit_document(tmp_path: Path) -> None:
    async def run_check() -> None:
        source = tmp_path / "notes.md"
        source.write_text("# Title\n\nBody", encoding="utf-8")

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            document = await ingest_document(source, audit_store=audit_store)
            stored = await audit_store.get_document(document.doc_id)

        assert detect_document_format(source) == "markdown"
        assert document.format == "markdown"
        assert len(document.source_map) == 1
        assert document.source_map[0].kind == "source"
        assert document.source_map[0].text_range.end_char == len(document.text)
        assert document.source_map[0].source_end_byte == len(document.text.encode("utf-8"))
        assert stored == document

    asyncio.run(run_check())


def test_ingest_pdf_uses_pdfplumber_pages_and_tracks_page_offsets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakePage:
        def __init__(self, text: str | None) -> None:
            self._text = text

        def extract_text(self) -> str | None:
            return self._text

    class FakePdf:
        pages = [FakePage("first page"), FakePage("second é")]

        def __enter__(self) -> "FakePdf":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    fake_pdfplumber = ModuleType("pdfplumber")
    fake_pdfplumber.open = lambda _path: FakePdf()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)

    async def run_check() -> None:
        source = tmp_path / "source.pdf"
        source.write_bytes(b"%PDF fake bytes")

        document = await ingest_document(source)

        assert document.format == "pdf"
        assert document.text == "first page\n\nsecond é"
        assert tuple(page.page_number for page in document.page_map) == (1, 2)
        assert document.page_map[0].start_char == 0
        assert document.page_map[0].end_char == len("first page")
        assert document.page_map[0].start_byte == 0
        assert document.page_map[0].end_byte == len("first page".encode("utf-8"))
        assert document.page_map[1].start_char == len("first page\n\n")
        assert document.page_map[1].end_char == len("first page\n\nsecond é")
        assert document.page_map[1].start_byte == len("first page\n\n".encode("utf-8"))
        assert document.page_map[1].end_byte == len("first page\n\nsecond é".encode("utf-8"))
        assert tuple(segment.kind for segment in document.source_map) == (
            "unmapped",
            "generated",
            "unmapped",
        )
        assert document.source_map[0].text_range.start_char == 0
        assert document.source_map[0].text_range.end_char == len("first page")
        assert document.source_map[1].text_range.start_char == len("first page")
        assert document.source_map[1].text_range.end_char == len("first page\n\n")
        assert document.source_map[1].source_start_byte is None
        assert document.source_map[1].source_end_byte is None
        assert document.source_map[2].text_range.start_char == len("first page\n\n")
        assert document.source_map[2].text_range.end_char == len("first page\n\nsecond é")

    asyncio.run(run_check())


def test_ingest_rejects_unsupported_empty_and_invalid_utf8_sources(tmp_path: Path) -> None:
    async def run_check() -> None:
        unsupported = tmp_path / "document.rtf"
        unsupported.write_bytes(b"content")
        empty_text = tmp_path / "empty.txt"
        empty_text.write_text("", encoding="utf-8")
        invalid_text = tmp_path / "invalid.txt"
        invalid_text.write_bytes(b"\xff")

        with pytest.raises(UnsupportedDocumentFormatError):
            await ingest_document(unsupported)

        with pytest.raises(EmptyDocumentError):
            await ingest_document(empty_text)

        with pytest.raises(IngestionError, match="valid UTF-8"):
            await ingest_document(invalid_text)

    asyncio.run(run_check())
