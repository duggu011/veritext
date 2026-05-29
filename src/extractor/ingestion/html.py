from __future__ import annotations

import codecs
from html.parser import HTMLParser
from pathlib import Path
import re
from typing import Literal

from extractor.contracts import PageSpan
from extractor.contracts.ingestion import (
    DocumentMetadata,
    LayoutSpan,
    MetadataEntry,
    SourceMapSegment,
    TableSpan,
    TextRange,
)
from extractor.ingestion.errors import EmptyDocumentError, IngestionError
from extractor.ingestion.html_tables import append_html_table_rows
from extractor.ingestion.pdf import PdfIngestionResult


HTML_MIME_TYPE = "text/html"
HTML_PARSER_NAME = "stdlib-html"
DEFAULT_HTML_ENCODING = "utf-8"

_CHARSET_RE = re.compile(rb"charset\s*=\s*['\"]?\s*([A-Za-z0-9._:-]+)", re.I)
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_IGNORED_TEXT_TAGS = {"script", "style"}
_BLOCK_ROLES = {
    "p": "paragraph",
    "li": "list_item",
}


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
        kind: Literal["generated", "unmapped"],
    ) -> TextRange:
        if text == "":
            raise IngestionError("HTML parser attempted to emit an empty text segment")

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

    def text(self) -> str:
        return "".join(self.parts)


class _HtmlBoundaryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.assembler = _TextAssembler()
        self.layout_spans: list[LayoutSpan] = []
        self.table_spans: list[TableSpan] = []
        self.title: str | None = None
        self.meta_entries: dict[str, str] = {}
        self.block_index = 0
        self.table_index = 0
        self._ignored_depth = 0
        self._in_title = False
        self._title_parts: list[str] = []
        self._current_block_tag: str | None = None
        self._current_block_role: Literal["heading", "paragraph", "list_item"] | None = None
        self._current_block_parts: list[str] = []
        self._table_stack: list[list[list[str]]] = []
        self._current_row: list[str] | None = None
        self._current_cell_parts: list[str] | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        tag = tag.lower()
        attr_map = {name.lower(): value for name, value in attrs if value is not None}

        if tag in _IGNORED_TEXT_TAGS:
            self._ignored_depth += 1
            return

        if tag == "title":
            self._in_title = True
            self._title_parts = []
            return

        if tag == "meta":
            self._capture_meta(attr_map)
            return

        if tag == "table":
            self._flush_open_block()
            self._table_stack.append([])
            return

        if self._table_stack:
            if tag == "tr":
                self._current_row = []
                return
            if tag in {"td", "th"}:
                self._current_cell_parts = []
                return

        if tag in _HEADING_TAGS:
            self._start_block(tag, "heading")
            return

        role = _BLOCK_ROLES.get(tag)
        if role is not None:
            self._start_block(tag, role)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _IGNORED_TEXT_TAGS and self._ignored_depth > 0:
            self._ignored_depth -= 1
            return

        if tag == "title":
            self.title = _normalize_text(self._title_parts) or None
            self._in_title = False
            self._title_parts = []
            return

        if self._table_stack:
            if tag in {"td", "th"}:
                self._close_table_cell()
                return
            if tag == "tr":
                self._close_table_row()
                return
            if tag == "table":
                rows = self._table_stack.pop()
                self._append_table(rows)
                return

        if tag == self._current_block_tag:
            self._flush_open_block()

    def handle_data(self, data: str) -> None:
        if self._ignored_depth > 0:
            return
        if self._in_title:
            self._title_parts.append(data)
            return
        if self._current_cell_parts is not None:
            self._current_cell_parts.append(data)
            return
        if self._current_block_tag is not None:
            self._current_block_parts.append(data)

    def _capture_meta(self, attrs: dict[str, str]) -> None:
        name = attrs.get("name")
        content = attrs.get("content")
        if name is None or content is None:
            return
        key = f"meta:{name.strip().lower()}"
        value = content.strip()
        if key != "meta:" and value and key not in self.meta_entries:
            self.meta_entries[key] = value

    def _start_block(
        self,
        tag: str,
        role: Literal["heading", "paragraph", "list_item"],
    ) -> None:
        self._flush_open_block()
        self._current_block_tag = tag
        self._current_block_role = role
        self._current_block_parts = []

    def _flush_open_block(self) -> None:
        if self._current_block_tag is None or self._current_block_role is None:
            return

        text = _normalize_text(self._current_block_parts)
        if text:
            self._append_block(text, self._current_block_role)
        self._current_block_tag = None
        self._current_block_role = None
        self._current_block_parts = []

    def _append_block(
        self,
        text: str,
        role: Literal["heading", "paragraph", "list_item"],
    ) -> None:
        if self.assembler.parts:
            self.assembler.add_segment(
                "\n",
                segment_id=f"generated:html:block-separator:{self.block_index}",
                kind="generated",
            )
        text_range = self.assembler.add_segment(
            text,
            segment_id=f"unmapped:html:block:{self.block_index}",
            kind="unmapped",
        )
        self.layout_spans.append(
            LayoutSpan(
                span_id=f"layout:html:1:block:{self.block_index}",
                page_number=1,
                role=role,
                text_range=text_range,
            )
        )
        self.block_index += 1

    def _close_table_cell(self) -> None:
        if self._current_cell_parts is None or self._current_row is None:
            return
        cell_text = _normalize_text(self._current_cell_parts)
        self._current_row.append(cell_text)
        self._current_cell_parts = None

    def _close_table_row(self) -> None:
        if self._current_row is None:
            return
        if self._table_stack and self._current_row:
            self._table_stack[-1].append(self._current_row)
        self._current_row = None

    def _append_table(self, rows: list[list[str]]) -> None:
        if not rows:
            return
        if self.assembler.parts:
            self.assembler.add_segment(
                "\n",
                segment_id=f"generated:html:block-separator:{self.block_index}",
                kind="generated",
            )

        table_span, table_layout, cell_layouts = append_html_table_rows(
            rows,
            assembler=self.assembler,
            table_index=self.table_index,
        )
        self.table_spans.append(table_span)
        self.layout_spans.append(table_layout)
        self.layout_spans.extend(cell_layouts)
        self.table_index += 1
        self.block_index += 1


def extract_html_document(source_path: Path, source_bytes: bytes) -> PdfIngestionResult:
    declared_encoding = _declared_charset(source_bytes) or DEFAULT_HTML_ENCODING
    try:
        codecs.lookup(declared_encoding)
    except LookupError as exc:
        raise IngestionError(
            f"HTML source declares unsupported charset {declared_encoding}: {source_path}"
        ) from exc

    try:
        html_text = source_bytes.decode(declared_encoding)
    except UnicodeDecodeError as exc:
        raise IngestionError(
            f"HTML source could not be decoded as {declared_encoding}: {source_path}"
        ) from exc

    parser = _HtmlBoundaryParser()
    try:
        parser.feed(html_text)
        parser.close()
    except Exception as exc:
        raise IngestionError(f"HTML parser failed for source document: {source_path}") from exc

    text = parser.assembler.text()
    if text == "":
        raise EmptyDocumentError(f"HTML source document yielded no visible text: {source_path}")

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
        source_map=tuple(parser.assembler.source_map),
        metadata=_document_metadata(source_path, declared_encoding, parser),
        layout_spans=tuple(parser.layout_spans),
        table_spans=tuple(parser.table_spans),
    )


def _document_metadata(
    source_path: Path,
    declared_encoding: str,
    parser: _HtmlBoundaryParser,
) -> DocumentMetadata:
    entries = [
        MetadataEntry(key=key, value=value)
        for key, value in sorted(parser.meta_entries.items())
    ]
    if parser.title is not None:
        entries.append(MetadataEntry(key="title", value=parser.title))
    return DocumentMetadata(
        source_name=source_path.name,
        mime_type=HTML_MIME_TYPE,
        parser_name=HTML_PARSER_NAME,
        declared_encoding=declared_encoding,
        raw_metadata=tuple(entries),
    )


def _declared_charset(source_bytes: bytes) -> str | None:
    sample = source_bytes[:4096]
    match = _CHARSET_RE.search(sample)
    if match is None:
        return None
    return match.group(1).decode("ascii").lower()


def _normalize_text(parts: list[str]) -> str:
    return " ".join("".join(parts).split())


__all__ = [
    "HTML_MIME_TYPE",
    "HTML_PARSER_NAME",
    "extract_html_document",
]
