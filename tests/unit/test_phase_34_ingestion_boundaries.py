import asyncio
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from extractor.audit import AuditStore
from extractor.contracts import Document, SourceMapSegment, SourceSpan
from extractor.ingestion import ingest_document
from extractor.source_support import require_source_backed_span, source_span_is_source_backed


def write_docx_fixture(path: Path) -> None:
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
</Types>
""",
        )
        archive.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Insurance Requirements</w:t></w:r></w:p>
  </w:body>
</w:document>
""",
        )


def write_html_fixture(path: Path) -> None:
    path.write_text(
        """<html>
  <head><title>Insurance Notice</title></head>
  <body>
    <h1>Insurance Requirements</h1>
    <table>
      <tr><th>Coverage</th><th>Limit</th></tr>
      <tr><td>General Liability</td><td>$2,000,000</td></tr>
    </table>
  </body>
</html>
""",
        encoding="utf-8",
    )


def write_email_fixture(path: Path) -> None:
    path.write_text(
        """Subject: Insurance Update
From: risk@example.com
To: ops@example.com
Content-Type: text/plain; charset=utf-8

Insurance Requirements
Vendor shall maintain coverage.
""",
        encoding="utf-8",
    )


def test_phase_34_formats_round_trip_boundary_payloads_through_audit_store(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        docx_path = tmp_path / "contract.docx"
        html_path = tmp_path / "notice.html"
        email_path = tmp_path / "notice.eml"
        write_docx_fixture(docx_path)
        write_html_fixture(html_path)
        write_email_fixture(email_path)

        async with AuditStore(tmp_path / "audit.sqlite3") as store:
            documents = (
                await ingest_document(docx_path, audit_store=store),
                await ingest_document(html_path, audit_store=store),
                await ingest_document(email_path, audit_store=store),
            )
            stored_documents = []
            for document in documents:
                stored_documents.append(await store.get_document(document.doc_id))

        assert tuple(stored_documents) == documents
        assert [document.metadata.parser_name for document in documents] == [
            "openxml-docx",
            "stdlib-html",
            "stdlib-email",
        ]
        assert [document.format for document in stored_documents] == [
            "docx",
            "html",
            "email",
        ]
        assert documents[1].table_spans[0].cells[3].header_labels == ("Limit",)
        assert tuple(segment.kind for segment in documents[2].source_map[:3]) == (
            "generated",
            "unmapped",
            "generated",
        )

    asyncio.run(run_check())


def test_phase_34_generated_and_unmapped_ranges_are_not_source_backed(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        docx_path = tmp_path / "contract.docx"
        html_path = tmp_path / "notice.html"
        email_path = tmp_path / "notice.eml"
        write_docx_fixture(docx_path)
        write_html_fixture(html_path)
        write_email_fixture(email_path)

        documents = (
            await ingest_document(docx_path),
            await ingest_document(html_path),
            await ingest_document(email_path),
        )

        for document in documents:
            for segment in _first_unmapped_and_generated_segments(document):
                span = _source_span_from_segment(document, segment)
                assert not source_span_is_source_backed(document, span)
                with pytest.raises(ValueError, match="generated or unmapped"):
                    require_source_backed_span(document, span)

    asyncio.run(run_check())


def _first_unmapped_and_generated_segments(
    document: Document,
) -> tuple[SourceMapSegment, ...]:
    segments: list[SourceMapSegment] = []
    for kind in ("unmapped", "generated"):
        for segment in document.source_map:
            if segment.kind == kind:
                segments.append(segment)
                break
    return tuple(segments)


def _source_span_from_segment(document: Document, segment: SourceMapSegment) -> SourceSpan:
    text_range = segment.text_range
    return SourceSpan(
        doc_id=document.doc_id,
        chunk_id="chunk-boundary-test",
        start_char=text_range.start_char,
        end_char=text_range.end_char,
        start_byte=text_range.start_byte,
        end_byte=text_range.end_byte,
        text=document.text[text_range.start_char : text_range.end_char],
    )
