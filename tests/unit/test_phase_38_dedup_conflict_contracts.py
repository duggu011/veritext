from __future__ import annotations

import importlib

from extractor.contracts import DataPoint, LensCandidate, SourceSpan
from extractor.executor import dedup


def make_source_span(
    *,
    chunk_id: str = "chunk-1",
    text: str = "Revenue increased",
    start_char: int = 0,
) -> SourceSpan:
    return SourceSpan(
        doc_id="doc-1",
        chunk_id=chunk_id,
        start_char=start_char,
        end_char=start_char + len(text),
        start_byte=start_char,
        end_byte=start_char + len(text.encode("utf-8")),
        text=text,
    )


def make_candidate(
    candidate_id: str,
    *,
    chunk_id: str = "chunk-1",
    lens: str = "claim",
    category: str = "Finding",
    field_name: str = "summary",
    value: str = "Revenue increased",
    source_text: str = "Revenue increased",
    start_char: int = 0,
    value_verbatim: str | None = None,
    value_canonical: str | None = None,
    value_kind: str = "text",
    normalization_status: str = "not_normalized",
    normalization_policy_id: str | None = None,
    normalization_policy_version: str | None = None,
) -> LensCandidate:
    return LensCandidate(
        candidate_id=candidate_id,
        run_id="run-1",
        doc_id="doc-1",
        chunk_id=chunk_id,
        lens=lens,
        category=category,
        field_name=field_name,
        value=value,
        source_span=make_source_span(
            chunk_id=chunk_id,
            text=source_text,
            start_char=start_char,
        ),
        confidence=0.8,
        executor_call_id=f"executor-{candidate_id}",
        value_verbatim=value_verbatim,
        value_canonical=value_canonical,
        value_kind=value_kind,
        normalization_status=normalization_status,
        normalization_policy_id=normalization_policy_id,
        normalization_policy_version=normalization_policy_version,
    )


def test_canonical_value_key_contract_records_policy_metadata() -> None:
    contracts = importlib.import_module("extractor.contracts")
    CanonicalValueKey = getattr(contracts, "CanonicalValueKey", None)

    assert CanonicalValueKey is not None, "CanonicalValueKey must be exported"

    key = CanonicalValueKey(
        kind="entity",
        key="acme inc",
        source="value_canonical",
        policy_id="entity-key",
        policy_version="2026-05-29",
    )

    assert key.kind == "entity"
    assert key.key == "acme inc"
    assert key.source == "value_canonical"
    assert key.policy_id == "entity-key"
    assert key.policy_version == "2026-05-29"


def test_dedup_cluster_contract_preserves_member_ids_and_span_count() -> None:
    contracts = importlib.import_module("extractor.contracts")
    CanonicalValueKey = getattr(contracts, "CanonicalValueKey", None)
    DedupCluster = getattr(contracts, "DedupCluster", None)

    assert CanonicalValueKey is not None, "CanonicalValueKey must be exported"
    assert DedupCluster is not None, "DedupCluster must be exported"

    cluster = DedupCluster(
        primary_candidate_id="candidate-a",
        merged_candidate_ids=("candidate-b",),
        all_candidate_ids=("candidate-a", "candidate-b"),
        canonical_key=CanonicalValueKey(kind="text", key="net 30", source="value"),
        source_span_count=2,
    )

    assert cluster.primary_candidate_id == "candidate-a"
    assert cluster.merged_candidate_ids == ("candidate-b",)
    assert cluster.all_candidate_ids == ("candidate-a", "candidate-b")
    assert cluster.source_span_count == 2


def test_legacy_data_point_payload_defaults_phase_38_additive_fields() -> None:
    payload = {
        "data_point_id": "dp-1",
        "run_id": "run-1",
        "doc_id": "doc-1",
        "category": "Finding",
        "field_name": "summary",
        "value": "Revenue increased",
        "source_span": make_source_span().model_dump(),
        "confidence": 0.8,
        "contributing_candidate_ids": ("candidate-a",),
        "critic_report_ids": ("critic-a",),
        "verifier_report_ids": ("verifier-a",),
        "reconciliation_decision_id": "decision-a",
    }

    data_point = DataPoint.model_validate(payload)

    assert getattr(data_point, "supporting_source_spans", None) == ()
    assert getattr(data_point, "conflict_status", None) == "none"
    assert getattr(data_point, "conflict_group_id", "missing") is None
    assert getattr(data_point, "conflict_reason", "missing") is None


def test_cross_chunk_duplicate_merges_when_source_span_identity_matches() -> None:
    first = make_candidate("candidate-a", chunk_id="chunk-1")
    duplicate = make_candidate("candidate-b", chunk_id="chunk-overlap")

    canonical, merged_into = dedup.deduplicate_candidates((duplicate, first))

    assert canonical == (first,)
    assert merged_into == {"candidate-b": "candidate-a"}


def test_canonicalized_duplicate_values_merge_with_dedup_cluster_detail() -> None:
    first = make_candidate(
        "candidate-a",
        value="net 30",
        source_text="Net-30",
        value_verbatim="Net-30",
        value_canonical="net 30",
        value_kind="duration",
        normalization_status="canonicalized",
        normalization_policy_id="duration-key",
        normalization_policy_version="2026-05-29",
    )
    duplicate = make_candidate(
        "candidate-b",
        chunk_id="chunk-2",
        value="net 30",
        source_text="NET 30",
        value_verbatim="NET 30",
        value_canonical="net 30",
        value_kind="duration",
        normalization_status="canonicalized",
        normalization_policy_id="duration-key",
        normalization_policy_version="2026-05-29",
    )

    canonical, merged_into = dedup.deduplicate_candidates((duplicate, first))
    clusters = dedup.build_dedup_clusters((duplicate, first))

    assert canonical == (first,)
    assert merged_into == {"candidate-b": "candidate-a"}
    assert len(clusters) == 1
    assert clusters[0].primary_candidate_id == "candidate-a"
    assert clusters[0].merged_candidate_ids == ("candidate-b",)
    assert clusters[0].all_candidate_ids == ("candidate-a", "candidate-b")
    assert clusters[0].canonical_key.key == "net 30"
    assert clusters[0].source_span_count == 2


def test_distinct_canonical_values_do_not_merge_as_conflicts() -> None:
    first = make_candidate(
        "candidate-a",
        value="30 days",
        value_verbatim="within thirty days",
        value_canonical="30 days",
        value_kind="duration",
        normalization_status="canonicalized",
        normalization_policy_id="duration-key",
        normalization_policy_version="2026-05-29",
    )
    conflict = make_candidate(
        "candidate-b",
        chunk_id="chunk-2",
        value="45 days",
        source_text="within forty five days",
        value_verbatim="within forty five days",
        value_canonical="45 days",
        value_kind="duration",
        normalization_status="canonicalized",
        normalization_policy_id="duration-key",
        normalization_policy_version="2026-05-29",
    )

    first_key = dedup.canonical_value_key_for_candidate(first)
    conflict_key = dedup.canonical_value_key_for_candidate(conflict)
    canonical, merged_into = dedup.deduplicate_candidates((conflict, first))
    clusters = dedup.build_dedup_clusters((conflict, first))

    assert first_key != conflict_key
    assert canonical == (first, conflict)
    assert merged_into == {}
    assert clusters == ()
