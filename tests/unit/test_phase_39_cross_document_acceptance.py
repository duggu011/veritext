from __future__ import annotations

from datetime import datetime, timezone

from extractor.contracts import (
    ApprovedSchemaMetadata,
    DataPoint,
    Document,
    PageSpan,
    RunManifest,
    SourceSpan,
)
from extractor.reconciler.cross_document import reconcile_cross_document_data_points


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
SCHEMA_HASH = "d" * 64


def test_source_neutral_cross_document_acceptance_preserves_provenance_and_conflicts() -> None:
    doc_a = make_document(
        "doc-a",
        "Record one lists status alpha. Supporting line repeats status alpha.",
        source_sha256=HASH_A,
    )
    doc_b = make_document(
        "doc-b",
        "Record two lists status alpha. Supporting line repeats status alpha.",
        source_sha256=HASH_B,
    )
    doc_c = make_document(
        "doc-c",
        "Record three lists status beta. Supporting line repeats status beta.",
        source_sha256=HASH_C,
    )
    alpha_a = make_data_point(
        run_id="run-a",
        doc=doc_a,
        data_point_id="dp-a",
        value="alpha",
        source_text="status alpha",
        conflict_status="unresolved",
        conflict_group_id="local-conflict-a",
        conflict_reason="same_field_distinct_canonical_values",
    )
    alpha_b = make_data_point(
        run_id="run-b",
        doc=doc_b,
        data_point_id="dp-b",
        value="alpha",
        source_text="status alpha",
    )
    beta_c = make_data_point(
        run_id="run-c",
        doc=doc_c,
        data_point_id="dp-c",
        value="beta",
        source_text="status beta",
    )

    result = reconcile_cross_document_data_points(
        cross_document_run_id="xrun-acceptance",
        data_points=(beta_c, alpha_b, alpha_a),
        documents=(doc_c, doc_b, doc_a),
        schema_metadata_by_run_id={
            "run-a": make_schema_metadata(),
            "run-b": make_schema_metadata(),
            "run-c": make_schema_metadata(),
        },
        run_manifests=(
            make_manifest(run_id="run-a", doc_id="doc-a", output_data_point_ids=("dp-a",)),
            make_manifest(run_id="run-b", doc_id="doc-b", output_data_point_ids=("dp-b",)),
            make_manifest(run_id="run-c", doc_id="doc-c", output_data_point_ids=("dp-c",)),
        ),
    )

    assert result.input_run_ids == ("run-a", "run-b", "run-c")
    assert result.input_doc_ids == ("doc-a", "doc-b", "doc-c")
    assert result.skipped_inputs == ()
    assert len(result.groups) == 2
    assert len(result.conflicts) == 1

    alpha_group = next(group for group in result.groups if group.key.canonical_key.key == "alpha")
    beta_group = next(group for group in result.groups if group.key.canonical_key.key == "beta")
    assert alpha_group.document_count == 2
    assert beta_group.document_count == 1
    assert alpha_group.conflict_status == "unresolved"
    assert beta_group.conflict_status == "unresolved"
    assert result.conflicts[0].conflicting_group_ids == tuple(
        sorted((alpha_group.group_id, beta_group.group_id))
    )
    assert result.conflicts[0].doc_ids == ("doc-a", "doc-b", "doc-c")

    source_a = next(source for source in alpha_group.sources if source.data_point_id == "dp-a")
    assert source_a.source_sha256 == HASH_A
    assert source_a.source_span.text == "status alpha"
    assert source_a.supporting_source_spans[0].text == "Supporting line repeats status alpha"
    assert source_a.conflict_status == "unresolved"
    assert source_a.conflict_group_id == "local-conflict-a"
    assert source_a.conflict_reason == "same_field_distinct_canonical_values"


def make_document(
    doc_id: str,
    text: str,
    *,
    source_sha256: str,
) -> Document:
    return Document(
        doc_id=doc_id,
        source_path=f"/tmp/{doc_id}.txt",
        format="plain_text",
        text=text,
        source_sha256=source_sha256,
        text_sha256=source_sha256,
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
    )


def make_data_point(
    *,
    run_id: str,
    doc: Document,
    data_point_id: str,
    value: str,
    source_text: str,
    conflict_status: str = "none",
    conflict_group_id: str | None = None,
    conflict_reason: str | None = None,
) -> DataPoint:
    supporting_text = f"Supporting line repeats status {value}"
    source_span = make_span(doc=doc, chunk_id=f"chunk-{doc.doc_id}", text=source_text)
    supporting_span = make_span(
        doc=doc,
        chunk_id=f"chunk-{doc.doc_id}",
        text=supporting_text,
    )
    return DataPoint(
        data_point_id=data_point_id,
        run_id=run_id,
        doc_id=doc.doc_id,
        category="RecordFact",
        field_name="status",
        value=value,
        source_span=source_span,
        confidence=0.91,
        contributing_candidate_ids=(f"candidate-{data_point_id}",),
        critic_report_ids=(f"critic-{data_point_id}",),
        verifier_report_ids=(f"verifier-{data_point_id}",),
        reconciliation_decision_id=f"decision-{data_point_id}",
        supporting_source_spans=(supporting_span,),
        conflict_status=conflict_status,
        conflict_group_id=conflict_group_id,
        conflict_reason=conflict_reason,
        value_verbatim=source_text,
        value_canonical=value,
        value_kind="text",
        normalization_status="canonicalized",
        normalization_policy_id="source-neutral-status",
        normalization_policy_version="1",
    )


def make_span(
    *,
    doc: Document,
    chunk_id: str,
    text: str,
) -> SourceSpan:
    start_char = doc.text.index(text)
    start_byte = len(doc.text[:start_char].encode("utf-8"))
    text_bytes = text.encode("utf-8")
    return SourceSpan(
        doc_id=doc.doc_id,
        chunk_id=chunk_id,
        start_char=start_char,
        end_char=start_char + len(text),
        start_byte=start_byte,
        end_byte=start_byte + len(text_bytes),
        text=text,
    )


def make_schema_metadata() -> ApprovedSchemaMetadata:
    return ApprovedSchemaMetadata(
        schema_id="schema:source-neutral-record",
        schema_version="1",
        schema_hash=SCHEMA_HASH,
        source_kind="planner_generated",
        created_from="planner",
    )


def make_manifest(
    *,
    run_id: str,
    doc_id: str,
    output_data_point_ids: tuple[str, ...],
) -> RunManifest:
    started_at = datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc)
    return RunManifest(
        run_id=run_id,
        doc_id=doc_id,
        audit_db_path="/tmp/audit.sqlite",
        status="completed",
        started_at=started_at,
        completed_at=datetime(2026, 5, 29, 12, 5, tzinfo=timezone.utc),
        output_data_point_ids=output_data_point_ids,
    )
