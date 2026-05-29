from __future__ import annotations

import codecs
from email import policy
from email.message import EmailMessage, Message
from email.parser import BytesParser
from pathlib import Path

from extractor.contracts import PageSpan
from extractor.contracts.ingestion import (
    DocumentMetadata,
    LayoutSpan,
    MetadataEntry,
    SourceMapSegment,
    TableCellSpan,
    TableSpan,
    TextRange,
)
from extractor.ingestion.errors import EmptyDocumentError, IngestionError
from extractor.ingestion.html import extract_html_document
from extractor.ingestion.pdf import PdfIngestionResult


EMAIL_MIME_TYPE = "message/rfc822"
EMAIL_PARSER_NAME = "stdlib-email"
DEFAULT_EMAIL_ENCODING = "utf-8"

_HEADER_ORDER = (
    ("Subject", "subject"),
    ("From", "from"),
    ("To", "to"),
    ("Cc", "cc"),
    ("Date", "date"),
)


class _TextAssembler:
    def __init__(self) -> None:
        self.parts: list[str] = []
        self.source_map: list[SourceMapSegment] = []
        self.current_char = 0
        self.current_byte = 0

    def add_segment(
        self,
        text: str,
        *,
        segment_id: str,
        kind: str,
    ) -> TextRange:
        if text == "":
            raise IngestionError("Email parser attempted to emit an empty text segment")

        start_char = self.current_char
        start_byte = self.current_byte
        text_bytes = text.encode("utf-8")
        self.parts.append(text)
        self.current_char += len(text)
        self.current_byte += len(text_bytes)
        text_range = TextRange(
            start_char=start_char,
            end_char=self.current_char,
            start_byte=start_byte,
            end_byte=self.current_byte,
        )
        self.source_map.append(
            SourceMapSegment(
                segment_id=segment_id,
                kind=kind,
                text_range=text_range,
            )
        )
        return text_range

    def import_result(self, result: PdfIngestionResult, *, segment_prefix: str) -> None:
        char_offset = self.current_char
        byte_offset = self.current_byte
        self.parts.append(result.text)
        self.current_char += len(result.text)
        self.current_byte += len(result.text.encode("utf-8"))
        for segment in result.source_map:
            if segment.kind == "source":
                raise IngestionError("Email HTML body must not include source-backed spans")
            self.source_map.append(
                SourceMapSegment(
                    segment_id=f"{segment_prefix}:{segment.segment_id}",
                    kind=segment.kind,
                    text_range=_shift_range(segment.text_range, char_offset, byte_offset),
                )
            )

    def text(self) -> str:
        return "".join(self.parts)


def extract_email_document(source_path: Path, source_bytes: bytes) -> PdfIngestionResult:
    try:
        message = BytesParser(policy=policy.default).parsebytes(source_bytes)
    except Exception as exc:
        raise IngestionError(f"Email parser failed for source document: {source_path}") from exc

    if message.defects:
        raise IngestionError(f"Email parser found message defects: {source_path}")

    _reject_attachments(message, source_path)
    body_part = _select_body_part(message, source_path)
    body_result = _extract_body(body_part, source_path)
    if body_result.text == "":
        raise EmptyDocumentError(f"Email source document yielded no body text: {source_path}")

    assembler = _TextAssembler()
    _append_headers(message, assembler)
    body_start_char = assembler.current_char
    body_start_byte = assembler.current_byte

    if body_result.layout_spans or body_result.table_spans or body_result.source_map:
        assembler.import_result(body_result, segment_prefix="email-body")
    else:
        assembler.add_segment(
            body_result.text,
            segment_id="unmapped:email:body",
            kind="unmapped",
        )

    text = assembler.text()
    if text == "":
        raise EmptyDocumentError(f"Email source document yielded no body text: {source_path}")

    return PdfIngestionResult(
        text=text,
        page_map=(
            PageSpan(
                page_number=1,
                start_char=0,
                end_char=len(text),
                start_byte=0,
                end_byte=len(text.encode("utf-8")),
            ),
        ),
        source_map=tuple(assembler.source_map),
        metadata=_document_metadata(message, body_part, source_path),
        layout_spans=_shift_layout_spans(
            body_result.layout_spans,
            body_start_char,
            body_start_byte,
        ),
        table_spans=_shift_table_spans(
            body_result.table_spans,
            body_start_char,
            body_start_byte,
        ),
    )


def _append_headers(message: Message, assembler: _TextAssembler) -> None:
    included_headers = [
        (label, str(message.get(name)))
        for label, name in _HEADER_ORDER
        if message.get(name) is not None and str(message.get(name)).strip()
    ]
    for index, (label, value) in enumerate(included_headers):
        assembler.add_segment(
            f"{label}: ",
            segment_id=f"generated:email:header-label:{label.lower()}",
            kind="generated",
        )
        assembler.add_segment(
            value.strip(),
            segment_id=f"unmapped:email:header-value:{label.lower()}",
            kind="unmapped",
        )
        assembler.add_segment(
            "\n\n" if index == len(included_headers) - 1 else "\n",
            segment_id=f"generated:email:header-separator:{index}",
            kind="generated",
        )


def _reject_attachments(message: Message, source_path: Path) -> None:
    for part in message.walk():
        if part is message:
            continue
        if part.get_content_disposition() == "attachment" or part.get_filename() is not None:
            raise IngestionError(f"Email attachments are not supported: {source_path}")
        if part.get_content_maintype() == "message":
            raise IngestionError(f"Email nested message parts are not supported: {source_path}")


def _select_body_part(message: Message, source_path: Path) -> Message:
    if not message.is_multipart():
        return message

    if message.get_content_type() != "multipart/alternative":
        raise IngestionError(f"Email multipart structure is unsupported: {source_path}")

    alternatives = list(message.iter_parts()) if isinstance(message, EmailMessage) else []
    for part in alternatives:
        if part.is_multipart():
            raise IngestionError(f"Email multipart alternatives must not be nested: {source_path}")
        if part.get_content_type() == "text/plain":
            return part
    for part in alternatives:
        if part.get_content_type() == "text/html":
            return part
    raise IngestionError(f"Email multipart alternative has no supported body: {source_path}")


def _extract_body(body_part: Message, source_path: Path) -> PdfIngestionResult:
    content_type = body_part.get_content_type()
    if content_type not in {"text/plain", "text/html"}:
        raise IngestionError(f"Email body content type is unsupported: {content_type}")

    charset = body_part.get_content_charset() or DEFAULT_EMAIL_ENCODING
    try:
        codecs.lookup(charset)
    except LookupError as exc:
        raise IngestionError(f"Email body declares unsupported charset {charset}: {source_path}") from exc

    decoded = _decode_part_payload(body_part, charset, source_path)
    if content_type == "text/html":
        try:
            return extract_html_document(source_path, decoded.encode("utf-8"))
        except EmptyDocumentError as exc:
            raise EmptyDocumentError(
                f"Email source document yielded no body text: {source_path}"
            ) from exc

    body_text = _normalize_plain_body(decoded)
    if body_text == "":
        raise EmptyDocumentError(f"Email source document yielded no body text: {source_path}")
    body_bytes = body_text.encode("utf-8")
    return PdfIngestionResult(
        text=body_text,
        page_map=(
            PageSpan(
                page_number=1,
                start_char=0,
                end_char=len(body_text),
                start_byte=0,
                end_byte=len(body_bytes),
            ),
        ),
        source_map=(),
        metadata=DocumentMetadata(declared_encoding=charset),
    )


def _decode_part_payload(body_part: Message, charset: str, source_path: Path) -> str:
    payload = body_part.get_payload(decode=True)
    try:
        if isinstance(payload, bytes):
            return payload.decode(charset)
        raw_payload = body_part.get_payload(decode=False)
        if isinstance(raw_payload, str):
            return raw_payload.encode("ascii", errors="surrogateescape").decode(charset)
    except UnicodeDecodeError as exc:
        raise IngestionError(f"Email body could not be decoded as {charset}: {source_path}") from exc
    raise IngestionError(f"Email body payload is unsupported: {source_path}")


def _normalize_plain_body(value: str) -> str:
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def _document_metadata(
    message: Message,
    body_part: Message,
    source_path: Path,
) -> DocumentMetadata:
    entries: list[MetadataEntry] = []
    raw_fields = (
        ("message_id", "Message-ID"),
        ("subject", "Subject"),
        ("from", "From"),
        ("to", "To"),
        ("cc", "Cc"),
        ("date", "Date"),
    )
    for key, header in raw_fields:
        value = message.get(header)
        if value is not None and str(value).strip():
            entries.append(MetadataEntry(key=key, value=str(value).strip()))
    entries.append(MetadataEntry(key="content_type", value=message.get_content_type()))

    return DocumentMetadata(
        source_name=source_path.name,
        mime_type=EMAIL_MIME_TYPE,
        parser_name=EMAIL_PARSER_NAME,
        declared_encoding=body_part.get_content_charset() or DEFAULT_EMAIL_ENCODING,
        raw_metadata=tuple(entries),
    )


def _shift_layout_spans(
    spans: tuple[LayoutSpan, ...],
    char_offset: int,
    byte_offset: int,
) -> tuple[LayoutSpan, ...]:
    return tuple(
        LayoutSpan(
            span_id=f"email-body:{span.span_id}",
            page_number=1,
            role=span.role,
            text_range=_shift_range(span.text_range, char_offset, byte_offset),
            bounding_box=None,
        )
        for span in spans
    )


def _shift_table_spans(
    tables: tuple[TableSpan, ...],
    char_offset: int,
    byte_offset: int,
) -> tuple[TableSpan, ...]:
    return tuple(
        TableSpan(
            table_id=f"email-body:{table.table_id}",
            page_number=1,
            text_range=_shift_range(table.text_range, char_offset, byte_offset),
            cells=tuple(
                TableCellSpan(
                    cell_id=f"email-body:{cell.cell_id}",
                    text_range=_shift_range(cell.text_range, char_offset, byte_offset),
                    row_index=cell.row_index,
                    column_index=cell.column_index,
                    row_span=cell.row_span,
                    column_span=cell.column_span,
                    header_labels=cell.header_labels,
                    bounding_box=None,
                )
                for cell in table.cells
            ),
            bounding_box=None,
        )
        for table in tables
    )


def _shift_range(text_range: TextRange, char_offset: int, byte_offset: int) -> TextRange:
    return TextRange(
        start_char=text_range.start_char + char_offset,
        end_char=text_range.end_char + char_offset,
        start_byte=text_range.start_byte + byte_offset,
        end_byte=text_range.end_byte + byte_offset,
    )


__all__ = [
    "EMAIL_MIME_TYPE",
    "EMAIL_PARSER_NAME",
    "extract_email_document",
]
