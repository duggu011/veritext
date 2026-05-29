from __future__ import annotations

from datetime import datetime, timezone
import importlib

from extractor.contracts import DataPoint, Document, PageSpan, SourceSpan
from extractor.reporter import build_static_provenance_artifact
from tests.unit.test_phase_40_run_diff import make_report
from tests.unit.test_reporter import HASH, make_data_point


GENERATED = datetime(2026, 5, 30, 17, 0, tzinfo=timezone.utc)


def _renderer():
    module = importlib.import_module("extractor.reporter")
    value = getattr(module, "render_static_provenance_html", None)
    assert value is not None, "render_static_provenance_html must be exported"
    return value


def make_document_with_text(text: str) -> Document:
    text_bytes = text.encode("utf-8")
    return Document(
        doc_id="doc-1",
        source_path="/tmp/source.txt",
        format="plain_text",
        text=text,
        source_sha256=HASH,
        text_sha256="b" * 64,
        source_byte_length=len(text_bytes),
        text_byte_length=len(text_bytes),
        page_map=(
            PageSpan(
                page_number=1,
                start_char=0,
                end_char=len(text),
                start_byte=0,
                end_byte=len(text_bytes),
            ),
        ),
    )


def make_point_from_document_text(text: str, source_text: str) -> DataPoint:
    start = text.index(source_text)
    span = SourceSpan(
        doc_id="doc-1",
        chunk_id="chunk-1",
        start_char=start,
        end_char=start + len(source_text),
        start_byte=start,
        end_byte=start + len(source_text.encode("utf-8")),
        text=source_text,
    )
    return make_data_point(value=source_text, start_char=start).model_copy(
        update={"source_span": span}
    )


def test_render_static_provenance_html_escapes_source_and_value_text() -> None:
    render_static_provenance_html = _renderer()
    source_text = "<script>alert(1)</script>"
    document_text = f"Before {source_text} after"
    point = make_point_from_document_text(document_text, source_text)
    artifact = build_static_provenance_artifact(
        report=make_report(run_id="run-1", data_points=(point,)),
        signed_manifest=None,
        document=make_document_with_text(document_text),
        candidate_rejections=(),
        diff_report=None,
        generated_at=GENERATED,
        context_radius=7,
    )

    html = render_static_provenance_html(artifact)

    assert html == render_static_provenance_html(artifact)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert 'id="data-point-dp-1"' in html
    assert "start_char" in html
    assert "end_byte" in html


def test_render_static_provenance_html_includes_warnings_and_optional_absence() -> None:
    render_static_provenance_html = _renderer()
    point = make_data_point().model_copy(
        update={
            "source_span": SourceSpan(
                doc_id="doc-1",
                chunk_id="chunk-1",
                start_char=0,
                end_char=len("Revenue INCREASED"),
                start_byte=0,
                end_byte=len("Revenue INCREASED".encode("utf-8")),
                text="Revenue INCREASED",
            )
        }
    )
    artifact = build_static_provenance_artifact(
        report=make_report(run_id="run-1", data_points=(point,)),
        signed_manifest=None,
        document=make_document_with_text("Revenue increased. Margin declined."),
        candidate_rejections=(),
        diff_report=None,
        generated_at=GENERATED,
        context_radius=8,
    )

    html = render_static_provenance_html(artifact)

    assert "source_span_text_mismatch" in html
    assert "signed_manifest_not_supplied" in html
    assert "run_diff_not_supplied" in html
    assert "Revenue INCREASED" in html
    assert "Revenue increased" in html
