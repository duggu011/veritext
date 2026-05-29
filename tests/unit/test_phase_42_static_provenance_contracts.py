from __future__ import annotations

from datetime import datetime, timezone
import importlib

import pytest
from pydantic import ValidationError

from extractor.contracts import SourceSpan


GENERATED = datetime(2026, 5, 30, 15, 0, tzinfo=timezone.utc)
SCHEMA_HASH = "a" * 64


def _contract(name: str):
    contracts = importlib.import_module("extractor.contracts")
    value = getattr(contracts, name, None)
    assert value is not None, f"{name} must be exported from extractor.contracts"
    return value


def make_span(
    *,
    text: str = "Revenue increased",
    start_char: int = 6,
) -> SourceSpan:
    return SourceSpan(
        doc_id="doc-1",
        chunk_id="chunk-1",
        start_char=start_char,
        end_char=start_char + len(text),
        start_byte=start_char,
        end_byte=start_char + len(text.encode("utf-8")),
        text=text,
    )


def make_context(*, data_point_id: str = "dp-1"):
    StaticProvenanceSourceContext = _contract("StaticProvenanceSourceContext")
    return StaticProvenanceSourceContext(
        data_point_id=data_point_id,
        source_span=make_span(),
        prefix_text="Alpha ",
        highlighted_text="Revenue increased",
        suffix_text=". Omega",
        offset_status="matched",
        mismatch_expected_text=None,
        mismatch_actual_text=None,
        warnings=(),
    )


def make_view(*, data_point_id: str = "dp-1"):
    StaticProvenanceDataPointView = _contract("StaticProvenanceDataPointView")
    return StaticProvenanceDataPointView(
        data_point_id=data_point_id,
        category="GenericFact",
        field_name="summary",
        value="Revenue increased",
        value_canonical=None,
        value_kind="text",
        confidence=0.91,
        confidence_bucket="verified",
        conflict_status="none",
        conflict_group_id=None,
        conflict_reason=None,
        source_context=make_context(data_point_id=data_point_id),
        contributing_candidate_ids=("candidate-1",),
        critic_report_ids=("critic-1",),
        verifier_report_ids=("verifier-1",),
        reconciliation_decision_id="decision-1",
        warnings=(),
    )


def test_static_provenance_contracts_preserve_ordered_data_point_views() -> None:
    StaticProvenanceArtifact = _contract("StaticProvenanceArtifact")
    view = make_view()

    artifact = StaticProvenanceArtifact(
        artifact_schema_version="static_provenance_artifact.v1",
        run_id="run-1",
        doc_id="doc-1",
        report_schema_version="report.v2",
        generated_at=GENERATED,
        report_artifact=None,
        schema_id="schema:generic",
        schema_hash=SCHEMA_HASH,
        schema_source_kind="planner_generated",
        output_data_point_ids=("dp-1",),
        manifest_identity=None,
        document_summary=None,
        data_point_views=(view,),
        rejection_summaries=(),
        diff_summary=None,
        warnings=(),
    )

    assert artifact.output_data_point_ids == ("dp-1",)
    assert artifact.data_point_views == (view,)

    with pytest.raises(ValidationError, match="output_data_point_ids"):
        StaticProvenanceArtifact(
            artifact_schema_version="static_provenance_artifact.v1",
            run_id="run-1",
            doc_id="doc-1",
            report_schema_version="report.v2",
            generated_at=GENERATED,
            report_artifact=None,
            schema_id="schema:generic",
            schema_hash=SCHEMA_HASH,
            schema_source_kind="planner_generated",
            output_data_point_ids=("different-id",),
            manifest_identity=None,
            document_summary=None,
            data_point_views=(view,),
            rejection_summaries=(),
            diff_summary=None,
            warnings=(),
        )


def test_static_source_context_builder_detects_match_and_mismatch() -> None:
    build_static_source_context = _contract("build_static_source_context")
    document_text = "Alpha Revenue increased. Omega"

    matched = build_static_source_context(
        data_point_id="dp-1",
        source_span=make_span(),
        document_text=document_text,
        context_radius=6,
    )

    assert matched.offset_status == "matched"
    assert matched.prefix_text == "Alpha "
    assert matched.highlighted_text == "Revenue increased"
    assert matched.suffix_text == ". Omeg"
    assert matched.warnings == ()

    mismatched = build_static_source_context(
        data_point_id="dp-1",
        source_span=make_span(text="Revenue INCREASED"),
        document_text=document_text,
        context_radius=6,
    )

    assert mismatched.offset_status == "mismatched"
    assert mismatched.mismatch_expected_text == "Revenue INCREASED"
    assert mismatched.mismatch_actual_text == "Revenue increased"
    assert mismatched.warnings[0].warning_code == "source_span_text_mismatch"


def test_static_data_point_view_rejects_context_identity_mismatch() -> None:
    StaticProvenanceDataPointView = _contract("StaticProvenanceDataPointView")

    with pytest.raises(ValidationError, match="source_context data_point_id"):
        StaticProvenanceDataPointView(
            data_point_id="dp-1",
            category="GenericFact",
            field_name="summary",
            value="Revenue increased",
            value_canonical=None,
            value_kind="text",
            confidence=0.91,
            confidence_bucket="verified",
            conflict_status="none",
            conflict_group_id=None,
            conflict_reason=None,
            source_context=make_context(data_point_id="dp-2"),
            contributing_candidate_ids=("candidate-1",),
            critic_report_ids=("critic-1",),
            verifier_report_ids=("verifier-1",),
            reconciliation_decision_id="decision-1",
            warnings=(),
        )
