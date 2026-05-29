from __future__ import annotations

import importlib
from typing import Callable

import pytest

from extractor.contracts import (
    ApprovedSchemaMetadata,
    DataPoint,
    Document,
    PageSpan,
    SourceSpan,
)


HASH_A = "a" * 64
HASH_B = "b" * 64
SCHEMA_HASH = "c" * 64
DOC_TEXT = "payment is due in 30 days; alternate says 45 days"


def _reconcile_service() -> Callable[..., object]:
    try:
        module = importlib.import_module("extractor.reconciler.cross_document")
    except ModuleNotFoundError:
        pytest.fail("extractor.reconciler.cross_document must provide Phase 39 service")
    service = getattr(module, "reconcile_cross_document_data_points", None)
    assert service is not None, "reconcile_cross_document_data_points must be exported"
    return service


def make_document(
    doc_id: str,
    *,
    source_sha256: str = HASH_A,
    text_sha256: str = HASH_B,
) -> Document:
    return Document(
        doc_id=doc_id,
        source_path=f"/tmp/{doc_id}.txt",
        format="plain_text",
        text=DOC_TEXT,
        source_sha256=source_sha256,
        text_sha256=text_sha256,
        source_byte_length=len(DOC_TEXT.encode("utf-8")),
        text_byte_length=len(DOC_TEXT.encode("utf-8")),
        page_map=(
            PageSpan(
                page_number=1,
                start_char=0,
                end_char=len(DOC_TEXT),
                start_byte=0,
                end_byte=len(DOC_TEXT.encode("utf-8")),
            ),
        ),
    )


def make_source_span(
    *,
    doc_id: str,
    chunk_id: str,
    text: str,
    start_char: int,
) -> SourceSpan:
    return SourceSpan(
        doc_id=doc_id,
        chunk_id=chunk_id,
        start_char=start_char,
        end_char=start_char + len(text),
        start_byte=start_char,
        end_byte=start_char + len(text.encode("utf-8")),
        text=text,
    )


def make_data_point(
    *,
    run_id: str,
    doc_id: str,
    data_point_id: str,
    value: str,
    source_text: str,
    start_char: int,
    normalization_status: str = "canonicalized",
    value_kind: str = "duration",
    value_verbatim: str | None = None,
    value_canonical: str | None = None,
) -> DataPoint:
    source_span = make_source_span(
        doc_id=doc_id,
        chunk_id=f"chunk-{doc_id[-1]}",
        text=source_text,
        start_char=start_char,
    )
    metadata = {}
    if normalization_status == "canonicalized":
        metadata = {
            "value_verbatim": value_verbatim or value,
            "value_canonical": value_canonical or value,
            "normalization_policy_id": "duration-key",
            "normalization_policy_version": "2026-05-29",
        }
    elif normalization_status == "verbatim_only":
        metadata = {"value_verbatim": value_verbatim or value}

    return DataPoint(
        data_point_id=data_point_id,
        run_id=run_id,
        doc_id=doc_id,
        category="PaymentTerm",
        field_name="payment_due",
        value=value,
        source_span=source_span,
        confidence=0.91,
        contributing_candidate_ids=(f"candidate-{data_point_id}",),
        critic_report_ids=(f"critic-{data_point_id}",),
        verifier_report_ids=(f"verifier-{data_point_id}",),
        reconciliation_decision_id=f"decision-{data_point_id}",
        supporting_source_spans=(source_span,),
        value_kind=value_kind,
        normalization_status=normalization_status,
        **metadata,
    )


def make_schema_metadata() -> ApprovedSchemaMetadata:
    return ApprovedSchemaMetadata(
        schema_id="schema:payment",
        schema_version="1",
        schema_hash=SCHEMA_HASH,
        source_kind="planner_generated",
        created_from="planner",
    )


def test_cross_document_reconciliation_groups_matching_canonical_values() -> None:
    reconcile = _reconcile_service()
    first = make_data_point(
        run_id="run-a",
        doc_id="doc-a",
        data_point_id="dp-a",
        value="30 days",
        source_text="payment is due in 30 days",
        start_char=0,
    )
    second = make_data_point(
        run_id="run-b",
        doc_id="doc-b",
        data_point_id="dp-b",
        value="30 days",
        source_text="payment is due in 30 days",
        start_char=0,
    )

    result = reconcile(
        cross_document_run_id="xrun-1",
        data_points=(second, first),
        documents=(
            make_document("doc-b", source_sha256="d" * 64, text_sha256="e" * 64),
            make_document("doc-a"),
        ),
        schema_metadata_by_run_id={
            "run-a": make_schema_metadata(),
            "run-b": make_schema_metadata(),
        },
    )
    repeat = reconcile(
        cross_document_run_id="xrun-1",
        data_points=(first, second),
        documents=(
            make_document("doc-a"),
            make_document("doc-b", source_sha256="d" * 64, text_sha256="e" * 64),
        ),
        schema_metadata_by_run_id={
            "run-a": make_schema_metadata(),
            "run-b": make_schema_metadata(),
        },
    )

    assert result == repeat
    assert result.input_run_ids == ("run-a", "run-b")
    assert result.input_doc_ids == ("doc-a", "doc-b")
    assert len(result.groups) == 1
    group = result.groups[0]
    assert group.document_count == 2
    assert group.conflict_status == "none"
    assert group.key.schema_id == "schema:payment"
    assert group.key.schema_hash == SCHEMA_HASH
    assert group.key.canonical_key.key == "30 days"
    assert tuple(source.doc_id for source in group.sources) == ("doc-a", "doc-b")
    assert tuple(source.source_sha256 for source in group.sources) == (HASH_A, "d" * 64)
    assert result.conflicts == ()
    assert result.skipped_inputs == ()


def test_cross_document_reconciliation_surfaces_distinct_canonical_conflicts() -> None:
    reconcile = _reconcile_service()
    thirty_days = make_data_point(
        run_id="run-a",
        doc_id="doc-a",
        data_point_id="dp-a",
        value="30 days",
        source_text="payment is due in 30 days",
        start_char=0,
    )
    forty_five_days = make_data_point(
        run_id="run-b",
        doc_id="doc-b",
        data_point_id="dp-b",
        value="45 days",
        source_text="alternate says 45 days",
        start_char=27,
    )

    result = reconcile(
        cross_document_run_id="xrun-conflict",
        data_points=(thirty_days, forty_five_days),
        documents=(make_document("doc-a"), make_document("doc-b")),
        schema_metadata_by_run_id={
            "run-a": make_schema_metadata(),
            "run-b": make_schema_metadata(),
        },
    )

    assert len(result.groups) == 2
    assert len(result.conflicts) == 1
    conflict = result.conflicts[0]
    assert conflict.reason == "same_field_distinct_canonical_values"
    assert conflict.category == "PaymentTerm"
    assert conflict.field_name == "payment_due"
    assert conflict.doc_ids == ("doc-a", "doc-b")
    assert set(conflict.conflicting_group_ids) == {group.group_id for group in result.groups}
    for group in result.groups:
        assert group.conflict_status == "unresolved"
        assert group.conflict_ids == (conflict.conflict_id,)


def test_cross_document_reconciliation_does_not_merge_unsafe_raw_text_near_matches() -> None:
    reconcile = _reconcile_service()
    first = make_data_point(
        run_id="run-a",
        doc_id="doc-a",
        data_point_id="dp-a",
        value="Acme Inc.",
        source_text="Acme Inc.",
        start_char=0,
        normalization_status="not_normalized",
        value_kind="entity",
    )
    near_match = make_data_point(
        run_id="run-b",
        doc_id="doc-b",
        data_point_id="dp-b",
        value="ACME, Inc",
        source_text="ACME, Inc",
        start_char=0,
        normalization_status="not_normalized",
        value_kind="entity",
    )

    result = reconcile(
        cross_document_run_id="xrun-raw",
        data_points=(near_match, first),
        documents=(make_document("doc-b"), make_document("doc-a")),
        schema_metadata_by_run_id={
            "run-a": make_schema_metadata(),
            "run-b": make_schema_metadata(),
        },
    )

    assert len(result.groups) == 2
    assert result.conflicts == ()
    assert [group.document_count for group in result.groups] == [1, 1]
    assert {group.key.canonical_key.key for group in result.groups} == {
        "acme inc",
        "acme, inc",
    }
