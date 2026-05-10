from __future__ import annotations

import asyncio
import hashlib
import importlib
from pathlib import Path
from typing import Literal

from extractor.audit import AuditStore
from extractor.contracts import Document, PageSpan
from extractor.contracts.ingestion import SourceMapSegment, TextRange
from extractor.contracts.models import DocumentFormat


TEXT_SUFFIXES = {".txt", ".text"}
MARKDOWN_SUFFIXES = {".md", ".markdown"}
PDF_SUFFIXES = {".pdf"}
PAGE_SEPARATOR = "\n\n"


class IngestionError(RuntimeError):
    """Base class for document ingestion failures."""


class UnsupportedDocumentFormatError(IngestionError):
    """Raised when a source file has no supported ingestion format."""


class EmptyDocumentError(IngestionError):
    """Raised when source extraction yields no document text."""


def detect_document_format(source_path: str | Path) -> DocumentFormat:
    suffix = Path(source_path).suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return "plain_text"
    if suffix in MARKDOWN_SUFFIXES:
        return "markdown"
    if suffix in PDF_SUFFIXES:
        return "pdf"
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

    text, page_map, source_map = await _extract_text_page_map_and_source_map(
        resolved_path,
        document_format,
        source_bytes,
    )
    text_bytes = text.encode("utf-8")
    if text == "":
        raise EmptyDocumentError(f"Source document yielded no text: {resolved_path}")

    document = Document(
        doc_id=f"doc-{source_sha256[:32]}",
        source_path=str(resolved_path),
        format=document_format,
        text=text,
        source_sha256=source_sha256,
        text_sha256=_sha256_hex(text_bytes),
        source_byte_length=len(source_bytes),
        text_byte_length=len(text_bytes),
        page_map=page_map,
        source_map=source_map,
    )

    if audit_store is not None:
        await audit_store.record_document(document)
    return document


async def _extract_text_page_map_and_source_map(
    source_path: Path,
    document_format: DocumentFormat,
    source_bytes: bytes,
) -> tuple[str, tuple[PageSpan, ...], tuple[SourceMapSegment, ...]]:
    if document_format in ("plain_text", "markdown"):
        text = _decode_utf8_source(source_bytes, source_path)
        source_map = _identity_source_map(text) if text else ()
        return text, (_single_page_span(text),), source_map

    if document_format == "pdf":
        return await asyncio.to_thread(_extract_pdf_text_and_page_map, source_path)

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


def _extract_pdf_text_and_page_map(
    source_path: Path,
) -> tuple[str, tuple[PageSpan, ...], tuple[SourceMapSegment, ...]]:
    try:
        pdfplumber = importlib.import_module("pdfplumber")
    except ImportError as exc:
        raise IngestionError("pdfplumber is required to ingest PDF documents") from exc

    page_texts: list[str] = []
    with pdfplumber.open(source_path) as pdf:
        for page in pdf.pages:
            page_texts.append(page.extract_text() or "")

    if not any(page_texts):
        raise EmptyDocumentError(f"PDF source document yielded no text: {source_path}")

    return _join_pages(page_texts)


def _join_pages(
    page_texts: list[str],
) -> tuple[str, tuple[PageSpan, ...], tuple[SourceMapSegment, ...]]:
    text_parts: list[str] = []
    page_map: list[PageSpan] = []
    source_map: list[SourceMapSegment] = []
    current_char = 0
    current_byte = 0

    for index, page_text in enumerate(page_texts, start=1):
        if text_parts:
            separator_start_char = current_char
            separator_start_byte = current_byte
            text_parts.append(PAGE_SEPARATOR)
            current_char += len(PAGE_SEPARATOR)
            current_byte += len(PAGE_SEPARATOR.encode("utf-8"))
            source_map.append(
                _unmapped_source_map_segment(
                    segment_id=f"generated:page-separator:{index - 1}:{index}",
                    kind="generated",
                    start_char=separator_start_char,
                    end_char=current_char,
                    start_byte=separator_start_byte,
                    end_byte=current_byte,
                )
            )

        page_start_char = current_char
        page_start_byte = current_byte
        page_bytes = page_text.encode("utf-8")
        text_parts.append(page_text)
        current_char += len(page_text)
        current_byte += len(page_bytes)
        if page_text:
            source_map.append(
                _unmapped_source_map_segment(
                    segment_id=f"unmapped:page:{index}",
                    kind="unmapped",
                    start_char=page_start_char,
                    end_char=current_char,
                    start_byte=page_start_byte,
                    end_byte=current_byte,
                )
            )
        page_map.append(
            PageSpan(
                page_number=index,
                start_char=page_start_char,
                end_char=current_char,
                start_byte=page_start_byte,
                end_byte=current_byte,
            )
        )

    return "".join(text_parts), tuple(page_map), tuple(source_map)


def _unmapped_source_map_segment(
    *,
    segment_id: str,
    kind: Literal["generated", "unmapped"],
    start_char: int,
    end_char: int,
    start_byte: int,
    end_byte: int,
) -> SourceMapSegment:
    return SourceMapSegment(
        segment_id=segment_id,
        kind=kind,
        text_range=TextRange(
            start_char=start_char,
            end_char=end_char,
            start_byte=start_byte,
            end_byte=end_byte,
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
