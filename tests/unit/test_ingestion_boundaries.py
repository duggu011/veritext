import pytest
from pydantic import ValidationError

from extractor.contracts import (
    BoundaryValidationContext,
    Document,
    DocumentMetadata,
    IngestionBoundarySet,
    LayoutSpan,
    OcrConfidenceSpan,
    PageSpan,
    SourceMapSegment,
    TableCellSpan,
    TableSpan,
    TextRange,
    validate_ingestion_boundaries,
)


def text_range(start: int, end: int) -> TextRange:
    return TextRange(start_char=start, end_char=end, start_byte=start, end_byte=end)


def source_segment(segment_id: str, start: int, end: int) -> SourceMapSegment:
    return SourceMapSegment(
        segment_id=segment_id,
        kind="source",
        text_range=text_range(start, end),
        source_start_byte=start,
        source_end_byte=end,
    )


def make_document(**overrides: object) -> Document:
    text = "alpha\n\nbeta"
    payload = {
        "doc_id": "doc-1",
        "source_path": "/tmp/source.txt",
        "format": "plain_text",
        "text": text,
        "source_sha256": "a" * 64,
        "text_sha256": "b" * 64,
        "source_byte_length": len(text.encode("utf-8")),
        "text_byte_length": len(text.encode("utf-8")),
        "page_map": (
            PageSpan(
                page_number=1,
                start_char=0,
                end_char=len(text),
                start_byte=0,
                end_byte=len(text.encode("utf-8")),
            ),
        ),
    }
    payload.update(overrides)
    return Document(**payload)


def test_source_map_segments_reject_invalid_source_backing() -> None:
    generated = SourceMapSegment(
        segment_id="sep-1",
        kind="generated",
        text_range=text_range(5, 7),
    )

    assert generated.source_start_byte is None
    assert generated.source_end_byte is None

    with pytest.raises(ValidationError):
        SourceMapSegment(
            segment_id="bad-generated",
            kind="generated",
            text_range=text_range(5, 7),
            source_start_byte=5,
            source_end_byte=7,
        )

    with pytest.raises(ValidationError):
        SourceMapSegment(
            segment_id="bad-source",
            kind="source",
            text_range=text_range(0, 5),
            source_start_byte=5,
            source_end_byte=5,
        )


def test_boundary_set_rejects_overlapping_source_map_segments_and_duplicate_cells() -> None:
    with pytest.raises(ValidationError):
        IngestionBoundarySet(
            source_map=(
                source_segment("seg-1", 0, 5),
                source_segment("seg-2", 4, 8),
            )
        )

    with pytest.raises(ValidationError):
        TableSpan(
            table_id="table-1",
            page_number=1,
            text_range=text_range(0, 10),
            cells=(
                TableCellSpan(
                    cell_id="cell-1",
                    text_range=text_range(0, 5),
                    row_index=0,
                    column_index=0,
                ),
                TableCellSpan(
                    cell_id="cell-1",
                    text_range=text_range(5, 10),
                    row_index=0,
                    column_index=1,
                ),
            ),
        )


def test_document_defaults_preserve_existing_constructor_compatibility() -> None:
    document = make_document()

    assert document.metadata == DocumentMetadata()
    assert document.source_map == ()
    assert document.layout_spans == ()
    assert document.table_spans == ()
    assert document.ocr_confidence_spans == ()


def test_document_validates_boundary_fields_against_text_source_and_pages() -> None:
    document = make_document(
        metadata=DocumentMetadata(source_name="source.txt", parser_name="plain-text"),
        source_map=(
            source_segment("seg-1", 0, 5),
            SourceMapSegment(
                segment_id="sep-1",
                kind="generated",
                text_range=text_range(5, 7),
            ),
            source_segment("seg-2", 7, 11),
        ),
        layout_spans=(
            LayoutSpan(
                span_id="layout-1",
                page_number=1,
                role="paragraph",
                text_range=text_range(0, 5),
            ),
        ),
        table_spans=(
            TableSpan(
                table_id="table-1",
                page_number=1,
                text_range=text_range(7, 11),
                cells=(
                    TableCellSpan(
                        cell_id="cell-1",
                        text_range=text_range(7, 11),
                        row_index=0,
                        column_index=0,
                    ),
                ),
            ),
        ),
        ocr_confidence_spans=(
            OcrConfidenceSpan(
                span_id="ocr-1",
                text_range=text_range(0, 5),
                confidence=0.75,
                engine="fixture-ocr",
            ),
        ),
    )

    assert document.metadata.source_name == "source.txt"
    assert tuple(segment.segment_id for segment in document.source_map) == (
        "seg-1",
        "sep-1",
        "seg-2",
    )

    with pytest.raises(ValidationError, match="source byte range exceeds"):
        make_document(
            source_map=(source_segment("seg-1", 0, 12),),
        )

    with pytest.raises(ValidationError, match="unknown page"):
        make_document(
            layout_spans=(
                LayoutSpan(
                    span_id="layout-1",
                    page_number=2,
                    role="paragraph",
                    text_range=text_range(0, 5),
                ),
            )
        )


def test_boundary_validation_rejects_ranges_outside_document_context() -> None:
    boundaries = IngestionBoundarySet(
        source_map=(
            source_segment("seg-1", 0, 5),
            SourceMapSegment(
                segment_id="sep-1",
                kind="generated",
                text_range=text_range(5, 7),
            ),
            source_segment("seg-2", 7, 11),
        ),
        layout_spans=(
            LayoutSpan(
                span_id="layout-1",
                page_number=1,
                role="paragraph",
                text_range=text_range(0, 5),
            ),
        ),
        table_spans=(
            TableSpan(
                table_id="table-1",
                page_number=1,
                text_range=text_range(7, 11),
                cells=(
                    TableCellSpan(
                        cell_id="cell-1",
                        text_range=text_range(7, 11),
                        row_index=0,
                        column_index=0,
                    ),
                ),
            ),
        ),
        ocr_confidence_spans=(
            OcrConfidenceSpan(
                span_id="ocr-1",
                text_range=text_range(0, 5),
                confidence=0.75,
                engine="fixture-ocr",
            ),
        ),
    )
    context = BoundaryValidationContext(
        text_length=11,
        text_byte_length=11,
        source_byte_length=11,
        page_numbers=(1,),
    )

    validate_ingestion_boundaries(boundaries, context)

    with pytest.raises(ValueError, match="source byte range exceeds"):
        validate_ingestion_boundaries(
            IngestionBoundarySet(source_map=(source_segment("seg-1", 0, 12),)),
            context,
        )

    with pytest.raises(ValueError, match="text range exceeds"):
        validate_ingestion_boundaries(
            IngestionBoundarySet(
                layout_spans=(
                    LayoutSpan(
                        span_id="layout-1",
                        page_number=1,
                        role="paragraph",
                        text_range=text_range(0, 12),
                    ),
                )
            ),
            context,
        )

    with pytest.raises(ValueError, match="unknown page"):
        validate_ingestion_boundaries(
            IngestionBoundarySet(
                layout_spans=(
                    LayoutSpan(
                        span_id="layout-1",
                        page_number=2,
                        role="paragraph",
                        text_range=text_range(0, 5),
                    ),
                )
            ),
            context,
        )
