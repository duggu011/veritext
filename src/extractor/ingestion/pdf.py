from __future__ import annotations

from dataclasses import dataclass, field
import importlib
from pathlib import Path
from typing import Literal

from extractor.contracts import PageSpan
from extractor.contracts.ingestion import (
    BoundingBox,
    DocumentMetadata,
    LayoutSpan,
    SourceMapSegment,
    TableCellSpan,
    TableSpan,
    TextRange,
)
from extractor.ingestion.errors import EmptyDocumentError, IngestionError


PAGE_SEPARATOR = "\n\n"


@dataclass(frozen=True)
class PdfIngestionResult:
    text: str
    page_map: tuple[PageSpan, ...]
    source_map: tuple[SourceMapSegment, ...]
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    layout_spans: tuple[LayoutSpan, ...] = ()
    table_spans: tuple[TableSpan, ...] = ()


def extract_pdf_document(
    source_path: Path,
    *,
    source_sha256: str | None = None,
) -> PdfIngestionResult:
    try:
        pdfplumber = importlib.import_module("pdfplumber")
    except ImportError as exc:
        raise IngestionError("pdfplumber is required to ingest PDF documents") from exc

    page_records: list[tuple[object, str]] = []
    try:
        with pdfplumber.open(source_path) as pdf:
            for page in pdf.pages:
                page_records.append((page, page.extract_text() or ""))
    except IngestionError:
        raise
    except Exception as exc:
        raise IngestionError(f"PDF parser failed for source document: {source_path}") from exc

    page_texts = [page_text for _, page_text in page_records]
    if not any(page_texts):
        raise EmptyDocumentError(f"PDF source document yielded no text: {source_path}")

    text, page_map, source_map = _join_pages(page_texts)
    try:
        layout_spans = tuple(
            span
            for (page, page_text), page_span in zip(page_records, page_map, strict=True)
            for span in _extract_layout_spans(page, page_text, page_span)
        )
        source_identity = source_sha256[:12] if source_sha256 is not None else source_path.stem
        table_spans = tuple(
            span
            for (page, page_text), page_span in zip(page_records, page_map, strict=True)
            for span in _extract_table_spans(
                page,
                page_text,
                page_span,
                source_identity=source_identity,
            )
        )
    except IngestionError:
        raise
    except Exception as exc:
        raise IngestionError(f"PDF parser failed for source document: {source_path}") from exc
    return PdfIngestionResult(
        text=text,
        page_map=page_map,
        source_map=source_map,
        metadata=DocumentMetadata(
            source_name=source_path.name,
            mime_type="application/pdf",
            parser_name="pdfplumber",
            parser_version=_parser_version(pdfplumber),
        ),
        layout_spans=layout_spans,
        table_spans=table_spans,
    )


def _parser_version(pdfplumber: object) -> str | None:
    version = getattr(pdfplumber, "__version__", None)
    if version is None:
        return None
    version_text = str(version)
    return version_text or None


def _extract_layout_spans(
    page: object,
    page_text: str,
    page_span: PageSpan,
) -> tuple[LayoutSpan, ...]:
    extract_words = getattr(page, "extract_words", None)
    if extract_words is None:
        return ()

    words = extract_words()
    layout_spans: list[LayoutSpan] = []
    cursor = 0
    for index, word in enumerate(words):
        if not isinstance(word, dict):
            raise IngestionError("PDF parser word output must be a mapping")
        word_text = word.get("text")
        if not isinstance(word_text, str) or word_text == "":
            raise IngestionError("PDF parser word output must include text")
        local_start = page_text.find(word_text, cursor)
        if local_start == -1:
            raise IngestionError(f"PDF word text could not be aligned: {word_text!r}")
        local_end = local_start + len(word_text)
        layout_spans.append(
            LayoutSpan(
                span_id=f"layout:page:{page_span.page_number}:word:{index}",
                page_number=page_span.page_number,
                role="unknown",
                text_range=_text_range_for_local_span(
                    page_text=page_text,
                    page_span=page_span,
                    local_start=local_start,
                    local_end=local_end,
                ),
                bounding_box=_word_bounding_box(word, page_span.page_number),
            )
        )
        cursor = local_end
    return tuple(layout_spans)


def _extract_table_spans(
    page: object,
    page_text: str,
    page_span: PageSpan,
    *,
    source_identity: str,
) -> tuple[TableSpan, ...]:
    find_tables = getattr(page, "find_tables", None)
    if find_tables is None:
        return ()

    table_spans: list[TableSpan] = []
    for table_offset, table in enumerate(find_tables()):
        rows = table.extract()
        cells: list[tuple[int, int, TextRange, tuple[str, ...]]] = []
        headers = _table_headers(rows)
        cursor = 0
        for row_index, row in enumerate(rows):
            if not isinstance(row, list):
                raise IngestionError("PDF parser table rows must be lists")
            for column_index, raw_cell_text in enumerate(row):
                cell_text = raw_cell_text if raw_cell_text is not None else ""
                if not isinstance(cell_text, str) or cell_text == "":
                    raise IngestionError("PDF parser table cell output must include text")
                local_start = page_text.find(cell_text, cursor)
                if local_start == -1:
                    raise IngestionError(
                        f"PDF table cell text could not be aligned: {cell_text!r}"
                    )
                local_end = local_start + len(cell_text)
                cells.append(
                    (
                        row_index,
                        column_index,
                        _text_range_for_local_span(
                            page_text=page_text,
                            page_span=page_span,
                            local_start=local_start,
                            local_end=local_end,
                        ),
                        _header_labels(headers, row_index, column_index),
                    )
                )
                cursor = local_end
        if not cells:
            raise IngestionError("PDF parser table output must include at least one cell")

        table_start = min(cell[2].start_char for cell in cells)
        table_end = max(cell[2].end_char for cell in cells)
        table_start_byte = min(cell[2].start_byte for cell in cells)
        table_end_byte = max(cell[2].end_byte for cell in cells)
        table_id = (
            f"table:{source_identity}:page:{page_span.page_number}:"
            f"{table_offset}:{table_start}:{table_end}"
        )
        table_range = TextRange(
            start_char=table_start,
            end_char=table_end,
            start_byte=table_start_byte,
            end_byte=table_end_byte,
        )
        table_spans.append(
            TableSpan(
                table_id=table_id,
                page_number=page_span.page_number,
                text_range=table_range,
                cells=tuple(
                    TableCellSpan(
                        cell_id=f"cell:{table_id}:r{row_index}:c{column_index}",
                        text_range=text_range,
                        row_index=row_index,
                        column_index=column_index,
                        header_labels=header_labels,
                    )
                    for row_index, column_index, text_range, header_labels in cells
                ),
                bounding_box=_table_bounding_box(table, page_span.page_number),
            )
        )
    return tuple(table_spans)


def _table_headers(rows: object) -> tuple[str, ...]:
    if not isinstance(rows, list) or not rows:
        raise IngestionError("PDF parser table output must include rows")
    first_row = rows[0]
    if not isinstance(first_row, list):
        raise IngestionError("PDF parser table rows must be lists")
    return tuple(cell if isinstance(cell, str) else "" for cell in first_row)


def _header_labels(
    headers: tuple[str, ...],
    row_index: int,
    column_index: int,
) -> tuple[str, ...]:
    if row_index == 0 or column_index >= len(headers) or headers[column_index] == "":
        return ()
    return (headers[column_index],)


def _word_bounding_box(word: dict[str, object], page_number: int) -> BoundingBox:
    try:
        x0 = float(word["x0"])
        y0 = float(word["top"])
        x1 = float(word["x1"])
        y1 = float(word["bottom"])
    except KeyError as exc:
        raise IngestionError("PDF parser word output must include bounding box coordinates") from exc
    return BoundingBox(page_number=page_number, x0=x0, y0=y0, x1=x1, y1=y1)


def _table_bounding_box(table: object, page_number: int) -> BoundingBox | None:
    bbox = getattr(table, "bbox", None)
    if bbox is None:
        return None
    if not isinstance(bbox, tuple) or len(bbox) != 4:
        raise IngestionError("PDF parser table bounding box must contain four coordinates")
    return BoundingBox(
        page_number=page_number,
        x0=float(bbox[0]),
        y0=float(bbox[1]),
        x1=float(bbox[2]),
        y1=float(bbox[3]),
    )


def _text_range_for_local_span(
    *,
    page_text: str,
    page_span: PageSpan,
    local_start: int,
    local_end: int,
) -> TextRange:
    start_char = page_span.start_char + local_start
    end_char = page_span.start_char + local_end
    start_byte = page_span.start_byte + len(page_text[:local_start].encode("utf-8"))
    end_byte = page_span.start_byte + len(page_text[:local_end].encode("utf-8"))
    return TextRange(
        start_char=start_char,
        end_char=end_char,
        start_byte=start_byte,
        end_byte=end_byte,
    )


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


__all__ = [
    "PAGE_SEPARATOR",
    "PdfIngestionResult",
    "extract_pdf_document",
]
