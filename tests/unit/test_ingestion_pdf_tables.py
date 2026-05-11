import asyncio
import sys
from pathlib import Path
from types import ModuleType

import pytest

from extractor.audit import AuditStore
from extractor.contracts import SourceSpan
from extractor.ingestion import IngestionError, ingest_document
from extractor.ingestion.pdf import extract_pdf_document
from extractor.source_support import require_source_backed_span, source_span_is_source_backed


class FakePage:
    def __init__(
        self,
        text: str | None,
        *,
        words: list[dict[str, object]] | None = None,
        tables: list["FakeTable"] | None = None,
    ) -> None:
        self._text = text
        self._words = words or []
        self._tables = tables or []

    def extract_text(self) -> str | None:
        return self._text

    def extract_words(self) -> list[dict[str, object]]:
        return self._words

    def find_tables(self) -> list["FakeTable"]:
        return self._tables


class FakeTable:
    def __init__(
        self,
        rows: list[list[str]],
        *,
        bbox: tuple[float, float, float, float] = (10.0, 20.0, 90.0, 60.0),
    ) -> None:
        self._rows = rows
        self.bbox = bbox

    def extract(self) -> list[list[str]]:
        return self._rows


class FakePdf:
    def __init__(self, pages: list[FakePage]) -> None:
        self.pages = pages

    def __enter__(self) -> "FakePdf":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def install_fake_pdfplumber(
    monkeypatch: pytest.MonkeyPatch,
    *,
    pages: list[FakePage],
    parser_version: str = "0.11.fake",
) -> None:
    fake_pdfplumber = ModuleType("pdfplumber")
    fake_pdfplumber.__version__ = parser_version
    fake_pdfplumber.open = lambda _path: FakePdf(pages)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)


def install_failing_pdfplumber(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_open(_path: Path) -> None:
        raise RuntimeError("parser exploded")

    fake_pdfplumber = ModuleType("pdfplumber")
    fake_pdfplumber.__version__ = "0.11.fake"
    fake_pdfplumber.open = fail_open  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)


def test_pdf_adapter_uses_fake_pdfplumber_pages_for_text_boundaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pdfplumber(
        monkeypatch,
        pages=[FakePage("first page"), FakePage("second é")],
    )
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF fake bytes")

    result = extract_pdf_document(source)

    assert result.text == "first page\n\nsecond é"
    assert tuple(page.page_number for page in result.page_map) == (1, 2)
    assert result.page_map[0].start_char == 0
    assert result.page_map[0].end_char == len("first page")
    assert result.page_map[1].start_char == len("first page\n\n")
    assert result.page_map[1].end_char == len("first page\n\nsecond é")
    assert tuple(segment.kind for segment in result.source_map) == (
        "unmapped",
        "generated",
        "unmapped",
    )
    assert result.source_map[1].segment_id == "generated:page-separator:1:2"
    assert result.source_map[1].source_start_byte is None
    assert result.source_map[1].source_end_byte is None


def test_pdf_adapter_populates_parser_metadata_and_layout_word_spans(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pdfplumber(
        monkeypatch,
        pages=[
            FakePage(
                "Overview élan",
                words=[
                    {"text": "Overview", "x0": 1.0, "top": 2.0, "x1": 5.0, "bottom": 6.0},
                    {"text": "élan", "x0": 6.0, "top": 2.0, "x1": 9.0, "bottom": 6.0},
                ],
            )
        ],
    )
    source = tmp_path / "layout.pdf"
    source.write_bytes(b"%PDF fake bytes")

    result = extract_pdf_document(source)

    assert result.metadata.source_name == "layout.pdf"
    assert result.metadata.mime_type == "application/pdf"
    assert result.metadata.parser_name == "pdfplumber"
    assert result.metadata.parser_version == "0.11.fake"
    assert tuple(span.span_id for span in result.layout_spans) == (
        "layout:page:1:word:0",
        "layout:page:1:word:1",
    )
    assert result.layout_spans[0].role == "unknown"
    assert result.layout_spans[0].text_range.start_char == 0
    assert result.layout_spans[0].text_range.end_char == len("Overview")
    assert result.layout_spans[1].text_range.start_char == len("Overview ")
    assert result.layout_spans[1].text_range.end_char == len("Overview élan")
    assert result.layout_spans[1].text_range.start_byte == len("Overview ".encode("utf-8"))
    assert result.layout_spans[1].text_range.end_byte == len("Overview élan".encode("utf-8"))
    assert result.layout_spans[0].bounding_box is not None
    assert result.layout_spans[0].bounding_box.page_number == 1
    assert result.layout_spans[0].bounding_box.x0 == 1.0
    assert result.layout_spans[0].bounding_box.y0 == 2.0
    assert result.layout_spans[0].bounding_box.x1 == 5.0
    assert result.layout_spans[0].bounding_box.y1 == 6.0


def test_pdf_adapter_populates_table_spans_and_cell_ranges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page_text = "Revenue table\nMetric Value\nRevenue $10\nCost $4"
    install_fake_pdfplumber(
        monkeypatch,
        pages=[
            FakePage(
                page_text,
                tables=[
                    FakeTable(
                        [
                            ["Metric", "Value"],
                            ["Revenue", "$10"],
                            ["Cost", "$4"],
                        ]
                    )
                ],
            )
        ],
    )
    source = tmp_path / "tables.pdf"
    source.write_bytes(b"%PDF fake bytes")

    result = extract_pdf_document(source, source_sha256="f" * 64)

    assert len(result.table_spans) == 1
    table = result.table_spans[0]
    table_start = page_text.index("Metric")
    assert table.table_id == f"table:{'f' * 12}:page:1:0:{table_start}:{len(page_text)}"
    assert table.page_number == 1
    assert table.text_range.start_char == table_start
    assert table.text_range.end_char == len(page_text)
    assert table.bounding_box is not None
    assert table.bounding_box.page_number == 1
    assert table.bounding_box.x0 == 10.0
    assert table.bounding_box.y0 == 20.0
    assert table.bounding_box.x1 == 90.0
    assert table.bounding_box.y1 == 60.0

    cells = table.cells
    assert [(cell.row_index, cell.column_index) for cell in cells] == [
        (0, 0),
        (0, 1),
        (1, 0),
        (1, 1),
        (2, 0),
        (2, 1),
    ]
    revenue_cell = cells[2]
    assert revenue_cell.cell_id == f"cell:{table.table_id}:r1:c0"
    assert revenue_cell.header_labels == ("Metric",)
    assert revenue_cell.text_range.start_char == page_text.index("Revenue", table_start)
    assert revenue_cell.text_range.end_char == revenue_cell.text_range.start_char + len("Revenue")
    value_cell = cells[3]
    assert value_cell.header_labels == ("Value",)
    assert value_cell.text_range.start_byte == len(
        page_text[: page_text.index("$10")].encode("utf-8")
    )
    assert value_cell.text_range.end_byte == len(
        page_text[: page_text.index("$10") + len("$10")].encode("utf-8")
    )


def test_pdf_adapter_rejects_unalignable_table_cells(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pdfplumber(
        monkeypatch,
        pages=[
            FakePage(
                "Metric Value\nRevenue $10",
                tables=[FakeTable([["Metric", "Value"], ["Missing", "$10"]])],
            )
        ],
    )
    source = tmp_path / "unalignable.pdf"
    source.write_bytes(b"%PDF fake bytes")

    with pytest.raises(IngestionError, match="PDF table cell text could not be aligned"):
        extract_pdf_document(source, source_sha256="f" * 64)


def test_pdf_adapter_rejects_no_text_and_wraps_parser_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "empty.pdf"
    source.write_bytes(b"%PDF fake bytes")
    install_fake_pdfplumber(monkeypatch, pages=[FakePage(None), FakePage("")])

    with pytest.raises(IngestionError, match="yielded no text"):
        extract_pdf_document(source, source_sha256="f" * 64)

    install_failing_pdfplumber(monkeypatch)
    with pytest.raises(IngestionError, match="PDF parser failed"):
        extract_pdf_document(source, source_sha256="f" * 64)


def test_ingest_pdf_records_table_boundaries_in_audit_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page_text = "Metric Value\nRevenue $10"
    install_fake_pdfplumber(
        monkeypatch,
        pages=[
            FakePage(
                page_text,
                words=[
                    {"text": "Metric", "x0": 1.0, "top": 1.0, "x1": 4.0, "bottom": 3.0},
                    {"text": "Value", "x0": 5.0, "top": 1.0, "x1": 8.0, "bottom": 3.0},
                    {"text": "Revenue", "x0": 1.0, "top": 4.0, "x1": 4.0, "bottom": 6.0},
                    {"text": "$10", "x0": 5.0, "top": 4.0, "x1": 8.0, "bottom": 6.0},
                ],
                tables=[FakeTable([["Metric", "Value"], ["Revenue", "$10"]])],
            )
        ],
    )
    source = tmp_path / "audit.pdf"
    source.write_bytes(b"%PDF fake bytes")

    async def run_check() -> None:
        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            document = await ingest_document(source, audit_store=audit_store)
            stored = await audit_store.get_document(document.doc_id)

        assert stored == document
        assert stored is not None
        assert stored.metadata.parser_name == "pdfplumber"
        assert stored.layout_spans[0].span_id == "layout:page:1:word:0"
        assert stored.table_spans[0].cells[2].header_labels == ("Metric",)
        assert tuple(segment.kind for segment in stored.source_map) == ("unmapped",)

    asyncio.run(run_check())


def test_ingested_pdf_unmapped_and_generated_ranges_are_not_source_backed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pdfplumber(
        monkeypatch,
        pages=[FakePage("first page"), FakePage("second page")],
    )
    source = tmp_path / "source-support.pdf"
    source.write_bytes(b"%PDF fake bytes")

    async def run_check() -> None:
        document = await ingest_document(source)
        first_page_span = SourceSpan(
            doc_id=document.doc_id,
            chunk_id="chunk-1",
            start_char=0,
            end_char=len("first page"),
            start_byte=0,
            end_byte=len("first page".encode("utf-8")),
            text="first page",
        )
        separator_span = SourceSpan(
            doc_id=document.doc_id,
            chunk_id="chunk-1",
            start_char=len("first page"),
            end_char=len("first page\n\n"),
            start_byte=len("first page".encode("utf-8")),
            end_byte=len("first page\n\n".encode("utf-8")),
            text="\n\n",
        )

        assert not source_span_is_source_backed(document, first_page_span)
        with pytest.raises(ValueError, match="generated or unmapped"):
            require_source_backed_span(document, first_page_span)
        assert not source_span_is_source_backed(document, separator_span)
        with pytest.raises(ValueError, match="generated or unmapped"):
            require_source_backed_span(document, separator_span)

    asyncio.run(run_check())
