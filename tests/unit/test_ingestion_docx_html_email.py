import asyncio
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from extractor.contracts import Document, PageSpan
from extractor.ingestion import IngestionError, detect_document_format, ingest_document


HASH = "a" * 64


def test_phase_34_detects_docx_html_and_email_formats() -> None:
    assert detect_document_format("contract.docx") == "docx"
    assert detect_document_format("notice.html") == "html"
    assert detect_document_format("notice.htm") == "html"
    assert detect_document_format("message.eml") == "email"
    assert detect_document_format("CONTRACT.DOCX") == "docx"
    assert detect_document_format("NOTICE.HTML") == "html"
    assert detect_document_format("MESSAGE.EML") == "email"


def test_document_contract_accepts_phase_34_formats() -> None:
    for document_format in ("docx", "html", "email"):
        document = Document(
            doc_id=f"doc-{document_format}",
            source_path=f"/tmp/source.{document_format}",
            format=document_format,
            text="alpha",
            source_sha256=HASH,
            text_sha256=HASH,
            source_byte_length=5,
            text_byte_length=5,
            page_map=(
                PageSpan(
                    page_number=1,
                    start_char=0,
                    end_char=5,
                    start_byte=0,
                    end_byte=5,
                ),
            ),
        )

        assert document.format == document_format


def write_docx_fixture(
    path: Path,
    *,
    document_xml: str,
    core_xml: str | None = None,
) -> None:
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
</Types>
""",
        )
        archive.writestr("word/document.xml", document_xml)
        if core_xml is not None:
            archive.writestr("docProps/core.xml", core_xml)


def test_ingest_docx_populates_metadata_layout_table_and_unmapped_source_map(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        source = tmp_path / "contract.docx"
        write_docx_fixture(
            source,
            document_xml="""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
      <w:r><w:t>Insurance Requirements</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>Vendor shall maintain coverage.</w:t></w:r>
    </w:p>
    <w:p>
      <w:pPr><w:numPr><w:ilvl w:val="0"/></w:numPr></w:pPr>
      <w:r><w:t>Additional insured endorsement required.</w:t></w:r>
    </w:p>
    <w:tbl>
      <w:tr>
        <w:tc><w:p><w:r><w:t>Coverage</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Limit</w:t></w:r></w:p></w:tc>
      </w:tr>
      <w:tr>
        <w:tc><w:p><w:r><w:t>General Liability</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>$2,000,000</w:t></w:r></w:p></w:tc>
      </w:tr>
    </w:tbl>
  </w:body>
</w:document>
""",
            core_xml="""<?xml version="1.0" encoding="UTF-8"?>
<cp:coreProperties
  xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Insurance Exhibit</dc:title>
  <dc:creator>Risk Team</dc:creator>
  <dcterms:created xsi:type="dcterms:W3CDTF">2026-05-01T10:30:00Z</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">2026-05-02T11:45:00Z</dcterms:modified>
</cp:coreProperties>
""",
        )

        document = await ingest_document(source)

        assert document.format == "docx"
        assert document.metadata.source_name == "contract.docx"
        assert document.metadata.mime_type == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert document.metadata.parser_name == "openxml-docx"
        assert {entry.key: entry.value for entry in document.metadata.raw_metadata} == {
            "creator": "Risk Team",
            "title": "Insurance Exhibit",
        }
        assert document.metadata.created_at is not None
        assert document.metadata.modified_at is not None
        assert document.text == (
            "Insurance Requirements\n"
            "Vendor shall maintain coverage.\n"
            "Additional insured endorsement required.\n"
            "Coverage Limit\n"
            "General Liability $2,000,000"
        )
        assert len(document.page_map) == 1
        assert document.page_map[0].start_char == 0
        assert document.page_map[0].end_char == len(document.text)
        assert tuple(segment.kind for segment in document.source_map) == (
            "unmapped",
            "generated",
            "unmapped",
            "generated",
            "unmapped",
            "generated",
            "unmapped",
            "generated",
            "unmapped",
        )
        assert all(segment.source_start_byte is None for segment in document.source_map)
        assert tuple(span.role for span in document.layout_spans) == (
            "heading",
            "paragraph",
            "list_item",
            "table",
            "table_cell",
            "table_cell",
            "table_cell",
            "table_cell",
        )
        assert len(document.table_spans) == 1
        table = document.table_spans[0]
        assert table.page_number == 1
        assert [cell.row_index for cell in table.cells] == [0, 0, 1, 1]
        assert [cell.column_index for cell in table.cells] == [0, 1, 0, 1]
        assert [cell.header_labels for cell in table.cells] == [
            (),
            (),
            ("Coverage",),
            ("Limit",),
        ]
        fourth_cell = table.cells[3].text_range
        assert document.text[fourth_cell.start_char : fourth_cell.end_char] == "$2,000,000"

    asyncio.run(run_check())


def test_ingest_docx_rejects_malformed_missing_document_and_empty_text(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        malformed = tmp_path / "malformed.docx"
        malformed.write_bytes(b"not a zip")

        missing_document = tmp_path / "missing.docx"
        with ZipFile(missing_document, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("docProps/core.xml", "<core />")

        empty = tmp_path / "empty.docx"
        write_docx_fixture(
            empty,
            document_xml="""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p /></w:body>
</w:document>
""",
        )

        with pytest.raises(IngestionError, match="DOCX parser failed"):
            await ingest_document(malformed)

        with pytest.raises(IngestionError, match="word/document.xml"):
            await ingest_document(missing_document)

        with pytest.raises(IngestionError, match="yielded no text"):
            await ingest_document(empty)

    asyncio.run(run_check())


def test_ingest_html_populates_metadata_layout_table_and_unmapped_source_map(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        source = tmp_path / "notice.html"
        source.write_text(
            """<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Insurance Notice</title>
    <meta name="author" content="Risk Team">
  </head>
  <body>
    <h1>Insurance Requirements</h1>
    <p>Vendor shall maintain coverage &amp; endorsements.</p>
    <ul>
      <li>Additional insured endorsement required.</li>
    </ul>
    <table>
      <tr><th>Coverage</th><th>Limit</th></tr>
      <tr><td>General Liability</td><td>$2,000,000</td></tr>
    </table>
    <script>ignoredScript()</script>
    <style>.ignored { color: red; }</style>
  </body>
</html>
""",
            encoding="utf-8",
        )

        document = await ingest_document(source)

        assert document.format == "html"
        assert document.metadata.source_name == "notice.html"
        assert document.metadata.mime_type == "text/html"
        assert document.metadata.parser_name == "stdlib-html"
        assert document.metadata.declared_encoding == "utf-8"
        assert {entry.key: entry.value for entry in document.metadata.raw_metadata} == {
            "meta:author": "Risk Team",
            "title": "Insurance Notice",
        }
        assert document.text == (
            "Insurance Requirements\n"
            "Vendor shall maintain coverage & endorsements.\n"
            "Additional insured endorsement required.\n"
            "Coverage Limit\n"
            "General Liability $2,000,000"
        )
        assert len(document.page_map) == 1
        assert document.page_map[0].start_char == 0
        assert document.page_map[0].end_char == len(document.text)
        assert tuple(segment.kind for segment in document.source_map) == (
            "unmapped",
            "generated",
            "unmapped",
            "generated",
            "unmapped",
            "generated",
            "unmapped",
            "generated",
            "unmapped",
        )
        assert all(segment.source_start_byte is None for segment in document.source_map)
        assert tuple(span.role for span in document.layout_spans) == (
            "heading",
            "paragraph",
            "list_item",
            "table",
            "table_cell",
            "table_cell",
            "table_cell",
            "table_cell",
        )
        assert len(document.table_spans) == 1
        table = document.table_spans[0]
        assert [cell.row_index for cell in table.cells] == [0, 0, 1, 1]
        assert [cell.column_index for cell in table.cells] == [0, 1, 0, 1]
        assert [cell.header_labels for cell in table.cells] == [
            (),
            (),
            ("Coverage",),
            ("Limit",),
        ]
        fourth_cell = table.cells[3].text_range
        assert document.text[fourth_cell.start_char : fourth_cell.end_char] == "$2,000,000"

    asyncio.run(run_check())


def test_ingest_html_rejects_empty_visible_text_and_unsupported_charset(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        empty = tmp_path / "empty.html"
        empty.write_text(
            """<html><body><script>ignored()</script><style>p { color: red; }</style></body></html>""",
            encoding="utf-8",
        )

        unsupported_charset = tmp_path / "unsupported.html"
        unsupported_charset.write_bytes(
            b'<html><head><meta charset="x-unknown"></head><body><p>alpha</p></body></html>'
        )

        with pytest.raises(IngestionError, match="yielded no visible text"):
            await ingest_document(empty)

        with pytest.raises(IngestionError, match="unsupported charset"):
            await ingest_document(unsupported_charset)

    asyncio.run(run_check())
