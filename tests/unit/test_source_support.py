import pytest

from extractor.contracts import Document, PageSpan, SourceMapSegment, SourceSpan, TextRange
from extractor.source_support import require_source_backed_span, source_span_is_source_backed


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


def make_document(*, with_source_map: bool = True) -> Document:
    text = "alpha\n\nbeta"
    source_map = ()
    if with_source_map:
        source_map = (
            source_segment("seg-1", 0, 5),
            SourceMapSegment(
                segment_id="sep-1",
                kind="generated",
                text_range=text_range(5, 7),
            ),
            source_segment("seg-2", 7, 11),
        )
    return Document(
        doc_id="doc-1",
        source_path="/tmp/source.txt",
        format="plain_text",
        text=text,
        source_sha256="a" * 64,
        text_sha256="b" * 64,
        source_byte_length=len(text.encode("utf-8")),
        text_byte_length=len(text.encode("utf-8")),
        page_map=(
            PageSpan(
                page_number=1,
                start_char=0,
                end_char=len(text),
                start_byte=0,
                end_byte=len(text.encode("utf-8")),
            ),
        ),
        source_map=source_map,
    )


def source_span(start: int, end: int) -> SourceSpan:
    text = "alpha\n\nbeta"[start:end]
    return SourceSpan(
        doc_id="doc-1",
        chunk_id="chunk-1",
        start_char=start,
        end_char=end,
        start_byte=start,
        end_byte=end,
        text=text,
    )


def test_source_backed_span_accepts_source_segments_and_rejects_generated_segments() -> None:
    document = make_document()

    assert source_span_is_source_backed(document, source_span(0, 5))
    require_source_backed_span(document, source_span(0, 5))

    assert not source_span_is_source_backed(document, source_span(5, 7))
    with pytest.raises(ValueError, match="generated or unmapped"):
        require_source_backed_span(document, source_span(5, 7))

    assert not source_span_is_source_backed(document, source_span(4, 8))
    with pytest.raises(ValueError, match="generated or unmapped"):
        require_source_backed_span(document, source_span(4, 8))


def test_source_backed_span_preserves_legacy_exact_span_behavior_without_source_map() -> None:
    document = make_document(with_source_map=False)

    assert source_span_is_source_backed(document, source_span(0, 5))
    require_source_backed_span(document, source_span(0, 5))

    mismatched = SourceSpan(
        doc_id="doc-1",
        chunk_id="chunk-1",
        start_char=0,
        end_char=5,
        start_byte=0,
        end_byte=5,
        text="omega",
    )
    assert not source_span_is_source_backed(document, mismatched)
