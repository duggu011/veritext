from __future__ import annotations

import hashlib
import importlib

import pytest

from extractor.reporter import build_static_provenance_artifact, render_static_provenance_html
from tests.unit.test_phase_40_run_diff import make_report
from tests.unit.test_phase_42_static_provenance_rendering import make_document_with_text
from tests.unit.test_reporter import make_data_point


def _writer():
    module = importlib.import_module("extractor.reporter")
    value = getattr(module, "write_static_provenance_html", None)
    assert value is not None, "write_static_provenance_html must be exported"
    return value


def _writer_error():
    module = importlib.import_module("extractor.reporter")
    value = getattr(module, "StaticProvenanceHtmlError", None)
    assert value is not None, "StaticProvenanceHtmlError must be exported"
    return value


def make_artifact():
    point = make_data_point().model_copy(update={"confidence": 0.91})
    return build_static_provenance_artifact(
        report=make_report(run_id="run-1", data_points=(point,)),
        signed_manifest=None,
        document=make_document_with_text("Revenue increased. Margin declined."),
        candidate_rejections=(),
        diff_report=None,
        generated_at=None,
        context_radius=8,
    )


def test_write_static_provenance_html_reports_hash_and_byte_length(tmp_path) -> None:
    write_static_provenance_html = _writer()
    artifact = make_artifact()
    output_path = tmp_path / "reports" / "run-1.provenance.html"

    result = write_static_provenance_html(
        artifact=artifact,
        output_path=output_path,
    )

    rendered = render_static_provenance_html(artifact)
    output_bytes = rendered.encode("utf-8")
    assert output_path.read_text(encoding="utf-8") == rendered
    assert result.artifact == artifact
    assert result.output_path == str(output_path)
    assert result.output_sha256 == hashlib.sha256(output_bytes).hexdigest()
    assert result.output_byte_length == len(output_bytes)


def test_write_static_provenance_html_rejects_directory_output(tmp_path) -> None:
    write_static_provenance_html = _writer()
    StaticProvenanceHtmlError = _writer_error()

    with pytest.raises(StaticProvenanceHtmlError, match="directory"):
        write_static_provenance_html(
            artifact=make_artifact(),
            output_path=tmp_path,
        )
