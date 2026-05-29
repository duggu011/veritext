from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from extractor.contracts import PageSpan
from extractor.contracts.ingestion import (
    LayoutSpan,
    SourceMapSegment,
    TableCellSpan,
    TableSpan,
    TextRange,
)
from extractor.ingestion.docx_metadata import (
    DOCX_MIME_TYPE,
    DOCX_PARSER_NAME,
    extract_docx_metadata,
)
from extractor.ingestion.errors import EmptyDocumentError, IngestionError
from extractor.ingestion.pdf import PdfIngestionResult


WORD_DOCUMENT_PATH = "word/document.xml"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

NS = {
    "w": W_NS,
}


@dataclass(frozen=True)
class _CellRecord:
    row_index: int
    column_index: int
    text_range: TextRange
    header_labels: tuple[str, ...]


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
            raise IngestionError("DOCX parser attempted to emit an empty text segment")

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


def extract_docx_document(source_path: Path) -> PdfIngestionResult:
    try:
        with ZipFile(source_path) as package:
            document_xml = _read_required_package_file(
                package,
                WORD_DOCUMENT_PATH,
                source_path,
            )
            metadata = extract_docx_metadata(package, source_path)
    except BadZipFile as exc:
        raise IngestionError(f"DOCX parser failed for source document: {source_path}") from exc

    try:
        root = ElementTree.fromstring(document_xml)
    except ElementTree.ParseError as exc:
        raise IngestionError(f"DOCX parser failed for source document: {source_path}") from exc

    assembler = _TextAssembler()
    layout_spans: list[LayoutSpan] = []
    table_spans: list[TableSpan] = []
    block_index = 0
    table_index = 0

    body = root.find("w:body", NS)
    if body is not None:
        for child in body:
            if child.tag == _word_tag("p"):
                paragraph_text = _paragraph_text(child)
                if paragraph_text == "":
                    continue
                if assembler.parts:
                    assembler.add_segment(
                        "\n",
                        segment_id=f"generated:docx:block-separator:{block_index}",
                        kind="generated",
                    )
                text_range = assembler.add_segment(
                    paragraph_text,
                    segment_id=f"unmapped:docx:block:{block_index}",
                    kind="unmapped",
                )
                layout_spans.append(
                    LayoutSpan(
                        span_id=f"layout:docx:1:block:{block_index}",
                        page_number=1,
                        role=_paragraph_role(child),
                        text_range=text_range,
                    )
                )
                block_index += 1

            if child.tag == _word_tag("tbl"):
                if assembler.parts:
                    assembler.add_segment(
                        "\n",
                        segment_id=f"generated:docx:block-separator:{block_index}",
                        kind="generated",
                    )
                table_result = _append_table(
                    child,
                    assembler=assembler,
                    table_index=table_index,
                )
                if table_result is None:
                    continue
                table_span, table_layout, cell_layouts = table_result
                table_spans.append(table_span)
                layout_spans.append(table_layout)
                layout_spans.extend(cell_layouts)
                table_index += 1
                block_index += 1

    text = assembler.text()
    if text == "":
        raise EmptyDocumentError(f"DOCX source document yielded no text: {source_path}")

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
        metadata=metadata,
        layout_spans=tuple(layout_spans),
        table_spans=tuple(table_spans),
    )


def _read_required_package_file(
    package: ZipFile,
    package_path: str,
    source_path: Path,
) -> bytes:
    try:
        return package.read(package_path)
    except KeyError as exc:
        raise IngestionError(f"DOCX package is missing {package_path}: {source_path}") from exc


def _append_table(
    table_element: ElementTree.Element,
    *,
    assembler: _TextAssembler,
    table_index: int,
) -> tuple[TableSpan, LayoutSpan, tuple[LayoutSpan, ...]] | None:
    rows = _table_rows(table_element)
    if not rows:
        return None

    table_start_char = assembler.current_char
    table_start_byte = assembler.current_byte
    headers = rows[0]
    cell_records: list[_CellRecord] = []

    for row_index, row in enumerate(rows):
        if row_index > 0:
            assembler.add_segment(
                "\n",
                segment_id=(
                    f"generated:docx:table:{table_index}:row-separator:{row_index - 1}"
                ),
                kind="generated",
            )

        row_text = " ".join(row)
        row_start_char = assembler.current_char
        row_start_byte = assembler.current_byte
        assembler.add_segment(
            row_text,
            segment_id=f"unmapped:docx:table:{table_index}:row:{row_index}",
            kind="unmapped",
        )

        local_char = 0
        for column_index, cell_text in enumerate(row):
            if cell_text == "":
                raise IngestionError("DOCX table cell output must include text")
            start_char = row_start_char + local_char
            end_char = start_char + len(cell_text)
            start_byte = row_start_byte + len(row_text[:local_char].encode("utf-8"))
            end_byte = row_start_byte + len(
                row_text[: local_char + len(cell_text)].encode("utf-8")
            )
            cell_records.append(
                _CellRecord(
                    row_index=row_index,
                    column_index=column_index,
                    text_range=TextRange(
                        start_char=start_char,
                        end_char=end_char,
                        start_byte=start_byte,
                        end_byte=end_byte,
                    ),
                    header_labels=_header_labels(headers, row_index, column_index),
                )
            )
            local_char += len(cell_text) + 1

    if not cell_records:
        return None

    table_id = (
        f"table:docx:1:{table_index}:{table_start_char}:{assembler.current_char}"
    )
    table_range = TextRange(
        start_char=table_start_char,
        end_char=assembler.current_char,
        start_byte=table_start_byte,
        end_byte=assembler.current_byte,
    )
    table_span = TableSpan(
        table_id=table_id,
        page_number=1,
        text_range=table_range,
        cells=tuple(
            TableCellSpan(
                cell_id=f"cell:{table_id}:r{cell.row_index}:c{cell.column_index}",
                text_range=cell.text_range,
                row_index=cell.row_index,
                column_index=cell.column_index,
                header_labels=cell.header_labels,
            )
            for cell in cell_records
        ),
    )
    table_layout = LayoutSpan(
        span_id=f"layout:docx:1:table:{table_index}",
        page_number=1,
        role="table",
        text_range=table_range,
    )
    cell_layouts = tuple(
        LayoutSpan(
            span_id=(
                f"layout:docx:1:table:{table_index}:"
                f"cell:{cell.row_index}:{cell.column_index}"
            ),
            page_number=1,
            role="table_cell",
            text_range=cell.text_range,
        )
        for cell in cell_records
    )
    return table_span, table_layout, cell_layouts


def _table_rows(table_element: ElementTree.Element) -> list[list[str]]:
    rows: list[list[str]] = []
    for row_element in table_element.findall("w:tr", NS):
        row: list[str] = []
        for cell_element in row_element.findall("w:tc", NS):
            cell_text = " ".join(
                paragraph_text
                for paragraph in cell_element.findall("w:p", NS)
                if (paragraph_text := _paragraph_text(paragraph)) != ""
            )
            row.append(cell_text)
        if row:
            rows.append(row)
    return rows


def _header_labels(
    headers: list[str],
    row_index: int,
    column_index: int,
) -> tuple[str, ...]:
    if row_index == 0 or column_index >= len(headers) or headers[column_index] == "":
        return ()
    return (headers[column_index],)


def _paragraph_role(paragraph: ElementTree.Element) -> Literal["heading", "list_item", "paragraph"]:
    p_properties = paragraph.find("w:pPr", NS)
    if p_properties is None:
        return "paragraph"

    style = p_properties.find("w:pStyle", NS)
    if style is not None:
        style_value = style.attrib.get(_word_tag("val"), "")
        if style_value.lower().startswith("heading"):
            return "heading"

    if p_properties.find("w:numPr", NS) is not None:
        return "list_item"
    return "paragraph"


def _paragraph_text(paragraph: ElementTree.Element) -> str:
    parts: list[str] = []
    for child in paragraph.iter():
        if child.tag == _word_tag("t") and child.text is not None:
            parts.append(child.text)
        elif child.tag == _word_tag("tab"):
            parts.append("\t")
        elif child.tag == _word_tag("br"):
            parts.append("\n")
    return "".join(parts).strip()


def _word_tag(local_name: str) -> str:
    return f"{{{W_NS}}}{local_name}"


__all__ = [
    "DOCX_MIME_TYPE",
    "DOCX_PARSER_NAME",
    "extract_docx_document",
]
