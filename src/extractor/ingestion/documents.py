from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

from extractor.audit import AuditStore
from extractor.contracts import Document, PageSpan
from extractor.contracts.ingestion import DocumentMetadata, SourceMapSegment, TextRange
from extractor.contracts.models import DocumentFormat
from extractor.ingestion.errors import (
    EmptyDocumentError,
    IngestionError,
    UnsupportedDocumentFormatError,
)
from extractor.ingestion.docx import extract_docx_document
from extractor.ingestion.pdf import PdfIngestionResult, extract_pdf_document
from extractor.ingestion.html import extract_html_document


TEXT_SUFFIXES = {".txt", ".text"}
MARKDOWN_SUFFIXES = {".md", ".markdown"}
PDF_SUFFIXES = {".pdf"}
DOCX_SUFFIXES = {".docx"}
HTML_SUFFIXES = {".html", ".htm"}
EMAIL_SUFFIXES = {".eml"}
def detect_document_format(source_path: str | Path) -> DocumentFormat:
    suffix = Path(source_path).suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return "plain_text"
    if suffix in MARKDOWN_SUFFIXES:
        return "markdown"
    if suffix in PDF_SUFFIXES:
        return "pdf"
    if suffix in DOCX_SUFFIXES:
        return "docx"
    if suffix in HTML_SUFFIXES:
        return "html"
    if suffix in EMAIL_SUFFIXES:
        return "email"
    raise UnsupportedDocumentFormatError(f"Unsupported document format for path: {source_path}")


async def ingest_document(
    source_path: str | Path,
    *,
    audit_store: AuditStore | None = None,
) -> Document:
    path = Path(source_path)
    if not path.is_file():
        raise IngestionError(f"Source document does not exist or is not a file: {source_path}")

    resolved_path = path.resolve()
    document_format = detect_document_format(resolved_path)
    source_bytes = await asyncio.to_thread(resolved_path.read_bytes)
    source_sha256 = _sha256_hex(source_bytes)

    extracted = await _extract_document_content(
        resolved_path,
        document_format,
        source_bytes,
    )
    text_bytes = extracted.text.encode("utf-8")
    if extracted.text == "":
        raise EmptyDocumentError(f"Source document yielded no text: {resolved_path}")

    document = Document(
        doc_id=f"doc-{source_sha256[:32]}",
        source_path=str(resolved_path),
        format=document_format,
        text=extracted.text,
        source_sha256=source_sha256,
        text_sha256=_sha256_hex(text_bytes),
        source_byte_length=len(source_bytes),
        text_byte_length=len(text_bytes),
        page_map=extracted.page_map,
        metadata=extracted.metadata,
        source_map=extracted.source_map,
        layout_spans=extracted.layout_spans,
        table_spans=extracted.table_spans,
    )

    if audit_store is not None:
        await audit_store.record_document(document)
    return document


async def _extract_document_content(
    source_path: Path,
    document_format: DocumentFormat,
    source_bytes: bytes,
) -> PdfIngestionResult:
    if document_format in ("plain_text", "markdown"):
        text = _decode_utf8_source(source_bytes, source_path)
        source_map = _identity_source_map(text) if text else ()
        return PdfIngestionResult(
            text=text,
            page_map=(_single_page_span(text),),
            source_map=source_map,
            metadata=DocumentMetadata(),
        )

    if document_format == "pdf":
        return await asyncio.to_thread(
            extract_pdf_document,
            source_path,
            source_sha256=_sha256_hex(source_bytes),
        )

    if document_format == "docx":
        return await asyncio.to_thread(extract_docx_document, source_path)

    if document_format == "html":
        return await asyncio.to_thread(extract_html_document, source_path, source_bytes)

    # This branch is unreachable when detect_document_format is used, but keeps
    # this boundary explicit if the supported formats expand.
    raise UnsupportedDocumentFormatError(f"Unsupported document format: {document_format}")


def _decode_utf8_source(source_bytes: bytes, source_path: Path) -> str:
    try:
        return source_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IngestionError(f"Source document must be valid UTF-8: {source_path}") from exc


def _single_page_span(text: str) -> PageSpan:
    return PageSpan(
        page_number=1,
        start_char=0,
        end_char=len(text),
        start_byte=0,
        end_byte=len(text.encode("utf-8")),
    )


def _identity_source_map(text: str) -> tuple[SourceMapSegment, ...]:
    text_bytes = text.encode("utf-8")
    return (
        SourceMapSegment(
            segment_id="source:0",
            kind="source",
            text_range=TextRange(
                start_char=0,
                end_char=len(text),
                start_byte=0,
                end_byte=len(text_bytes),
            ),
            source_start_byte=0,
            source_end_byte=len(text_bytes),
            source_start_char=0,
            source_end_char=len(text),
        ),
    )


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


__all__ = [
    "EmptyDocumentError",
    "IngestionError",
    "UnsupportedDocumentFormatError",
    "detect_document_format",
    "ingest_document",
]
