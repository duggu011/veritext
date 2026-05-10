from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from extractor.contracts.base import (
    Confidence,
    ContractModel,
    NonEmptyStr,
    NonNegativeInt,
    PositiveInt,
    Timestamp,
)


Coordinate = Annotated[float, Field(strict=True)]
LayoutRole = Literal[
    "page_header",
    "page_footer",
    "heading",
    "paragraph",
    "list_item",
    "table",
    "table_cell",
    "figure_caption",
    "unknown",
]
SourceMapSegmentKind = Literal["source", "generated", "unmapped"]


class TextRange(ContractModel):
    start_char: NonNegativeInt
    end_char: NonNegativeInt
    start_byte: NonNegativeInt
    end_byte: NonNegativeInt

    @model_validator(mode="after")
    def validate_offsets(self) -> TextRange:
        if self.end_char <= self.start_char:
            raise ValueError("end_char must be greater than start_char")
        if self.end_byte <= self.start_byte:
            raise ValueError("end_byte must be greater than start_byte")
        return self


class MetadataEntry(ContractModel):
    key: NonEmptyStr
    value: NonEmptyStr


class DocumentMetadata(ContractModel):
    source_name: NonEmptyStr | None = None
    mime_type: NonEmptyStr | None = None
    parser_name: NonEmptyStr | None = None
    parser_version: NonEmptyStr | None = None
    declared_encoding: NonEmptyStr | None = None
    created_at: Timestamp | None = None
    modified_at: Timestamp | None = None
    raw_metadata: tuple[MetadataEntry, ...] = ()

    @model_validator(mode="after")
    def validate_metadata_keys(self) -> DocumentMetadata:
        keys = [entry.key for entry in self.raw_metadata]
        if len(keys) != len(set(keys)):
            raise ValueError("raw_metadata keys must be unique")
        return self


class BoundingBox(ContractModel):
    page_number: PositiveInt
    x0: Coordinate
    y0: Coordinate
    x1: Coordinate
    y1: Coordinate

    @model_validator(mode="after")
    def validate_box(self) -> BoundingBox:
        if self.x1 < self.x0:
            raise ValueError("x1 must be greater than or equal to x0")
        if self.y1 < self.y0:
            raise ValueError("y1 must be greater than or equal to y0")
        return self


class SourceMapSegment(ContractModel):
    segment_id: NonEmptyStr
    kind: SourceMapSegmentKind
    text_range: TextRange
    source_start_byte: NonNegativeInt | None = None
    source_end_byte: NonNegativeInt | None = None
    source_start_char: NonNegativeInt | None = None
    source_end_char: NonNegativeInt | None = None

    @model_validator(mode="after")
    def validate_source_mapping(self) -> SourceMapSegment:
        has_source_bytes = self.source_start_byte is not None or self.source_end_byte is not None
        has_source_chars = self.source_start_char is not None or self.source_end_char is not None

        if self.kind == "source":
            if self.source_start_byte is None or self.source_end_byte is None:
                raise ValueError("source segments must include source byte offsets")
            if self.source_end_byte <= self.source_start_byte:
                raise ValueError("source_end_byte must be greater than source_start_byte")
            if has_source_chars:
                if self.source_start_char is None or self.source_end_char is None:
                    raise ValueError("source character offsets must be provided together")
                if self.source_end_char <= self.source_start_char:
                    raise ValueError("source_end_char must be greater than source_start_char")
            return self

        if has_source_bytes or has_source_chars:
            raise ValueError("generated or unmapped segments must not include source offsets")
        return self


class LayoutSpan(ContractModel):
    span_id: NonEmptyStr
    page_number: PositiveInt
    role: LayoutRole
    text_range: TextRange
    bounding_box: BoundingBox | None = None

    @model_validator(mode="after")
    def validate_box_page(self) -> LayoutSpan:
        if self.bounding_box is not None and self.bounding_box.page_number != self.page_number:
            raise ValueError("bounding_box page_number must match layout span page_number")
        return self


class TableCellSpan(ContractModel):
    cell_id: NonEmptyStr
    text_range: TextRange
    row_index: NonNegativeInt
    column_index: NonNegativeInt
    row_span: PositiveInt = 1
    column_span: PositiveInt = 1
    header_labels: tuple[NonEmptyStr, ...] = ()
    bounding_box: BoundingBox | None = None


class TableSpan(ContractModel):
    table_id: NonEmptyStr
    page_number: PositiveInt
    text_range: TextRange
    cells: tuple[TableCellSpan, ...] = Field(min_length=1)
    bounding_box: BoundingBox | None = None

    @model_validator(mode="after")
    def validate_table(self) -> TableSpan:
        cell_ids = [cell.cell_id for cell in self.cells]
        if len(cell_ids) != len(set(cell_ids)):
            raise ValueError("table cell ids must be unique")
        if self.bounding_box is not None and self.bounding_box.page_number != self.page_number:
            raise ValueError("bounding_box page_number must match table page_number")
        for cell in self.cells:
            if cell.text_range.start_char < self.text_range.start_char:
                raise ValueError("table cell text range must be within table text range")
            if cell.text_range.end_char > self.text_range.end_char:
                raise ValueError("table cell text range must be within table text range")
            if cell.text_range.start_byte < self.text_range.start_byte:
                raise ValueError("table cell byte range must be within table byte range")
            if cell.text_range.end_byte > self.text_range.end_byte:
                raise ValueError("table cell byte range must be within table byte range")
            if cell.bounding_box is not None and cell.bounding_box.page_number != self.page_number:
                raise ValueError("table cell bounding_box page_number must match table page_number")
        return self


class OcrConfidenceSpan(ContractModel):
    span_id: NonEmptyStr
    text_range: TextRange
    confidence: Confidence
    engine: NonEmptyStr | None = None


class IngestionBoundarySet(ContractModel):
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    source_map: tuple[SourceMapSegment, ...] = ()
    layout_spans: tuple[LayoutSpan, ...] = ()
    table_spans: tuple[TableSpan, ...] = ()
    ocr_confidence_spans: tuple[OcrConfidenceSpan, ...] = ()

    @model_validator(mode="after")
    def validate_boundaries(self) -> IngestionBoundarySet:
        _require_unique_ids(
            "source_map segment_id",
            (segment.segment_id for segment in self.source_map),
        )
        _require_unique_ids("layout span_id", (span.span_id for span in self.layout_spans))
        _require_unique_ids("table_id", (table.table_id for table in self.table_spans))
        _require_unique_ids(
            "ocr confidence span_id",
            (span.span_id for span in self.ocr_confidence_spans),
        )
        _validate_ordered_contiguous_source_map(self.source_map)
        return self


class BoundaryValidationContext(ContractModel):
    text_length: NonNegativeInt
    text_byte_length: NonNegativeInt
    source_byte_length: NonNegativeInt
    page_numbers: tuple[PositiveInt, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_page_numbers(self) -> BoundaryValidationContext:
        if len(self.page_numbers) != len(set(self.page_numbers)):
            raise ValueError("page_numbers must be unique")
        return self


def validate_ingestion_boundaries(
    boundaries: IngestionBoundarySet,
    context: BoundaryValidationContext,
) -> None:
    page_numbers = set(context.page_numbers)
    for segment in boundaries.source_map:
        if segment.kind == "source" and segment.source_end_byte > context.source_byte_length:
            raise ValueError("source byte range exceeds document source byte length")
        _ensure_text_range_within_context(segment.text_range, context)
    if boundaries.source_map:
        last_range = boundaries.source_map[-1].text_range
        if last_range.end_char != context.text_length:
            raise ValueError("source_map text ranges must cover document text")
        if last_range.end_byte != context.text_byte_length:
            raise ValueError("source_map byte ranges must cover document text bytes")

    for span in boundaries.layout_spans:
        _ensure_page_known(span.page_number, page_numbers)
        _ensure_box_page_known(span.bounding_box, page_numbers)
        _ensure_text_range_within_context(span.text_range, context)

    for table in boundaries.table_spans:
        _ensure_page_known(table.page_number, page_numbers)
        _ensure_box_page_known(table.bounding_box, page_numbers)
        _ensure_text_range_within_context(table.text_range, context)
        for cell in table.cells:
            _ensure_box_page_known(cell.bounding_box, page_numbers)
            _ensure_text_range_within_context(cell.text_range, context)

    for span in boundaries.ocr_confidence_spans:
        _ensure_text_range_within_context(span.text_range, context)


def _require_unique_ids(label: str, ids: object) -> None:
    values = tuple(ids)
    if len(values) != len(set(values)):
        raise ValueError(f"{label} values must be unique")


def _validate_ordered_contiguous_source_map(segments: tuple[SourceMapSegment, ...]) -> None:
    previous_char_end = 0
    previous_byte_end = 0
    for segment in segments:
        if segment.text_range.start_char < previous_char_end:
            raise ValueError("source_map text ranges must be ordered and non-overlapping")
        if segment.text_range.start_byte < previous_byte_end:
            raise ValueError("source_map byte ranges must be ordered and non-overlapping")
        if segment.text_range.start_char > previous_char_end:
            raise ValueError("source_map text ranges must be contiguous")
        if segment.text_range.start_byte > previous_byte_end:
            raise ValueError("source_map byte ranges must be contiguous")
        previous_char_end = segment.text_range.end_char
        previous_byte_end = segment.text_range.end_byte


def _ensure_text_range_within_context(
    text_range: TextRange,
    context: BoundaryValidationContext,
) -> None:
    if text_range.end_char > context.text_length:
        raise ValueError("text range exceeds document text length")
    if text_range.end_byte > context.text_byte_length:
        raise ValueError("text range exceeds document text byte length")


def _ensure_page_known(page_number: int, page_numbers: set[int]) -> None:
    if page_number not in page_numbers:
        raise ValueError("unknown page number in ingestion boundary")


def _ensure_box_page_known(
    bounding_box: BoundingBox | None,
    page_numbers: set[int],
) -> None:
    if bounding_box is not None:
        _ensure_page_known(bounding_box.page_number, page_numbers)


__all__ = [
    "BoundaryValidationContext",
    "BoundingBox",
    "DocumentMetadata",
    "IngestionBoundarySet",
    "LayoutRole",
    "LayoutSpan",
    "MetadataEntry",
    "OcrConfidenceSpan",
    "SourceMapSegment",
    "SourceMapSegmentKind",
    "TableCellSpan",
    "TableSpan",
    "TextRange",
    "validate_ingestion_boundaries",
]
