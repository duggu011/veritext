from __future__ import annotations

from extractor.contracts import (
    CategoryDefinition,
    ChunkPolicy,
    CriticReport,
    ExtractionBudget,
    ExtractionPlan,
    FieldDefinition,
    LensBudget,
    LensCandidate,
    SourceSpan,
    VerifierReport,
)
from extractor.llm import Complaints
from extractor.llm.views import build_candidate_view_map, short_candidate_id
from extractor.reconciler.batching import validate_reconciliation_batch
from extractor.reconciler.materialization import build_reconciliation_result
from extractor.reconciler.models import ReconciliationBatch


def make_plan() -> ExtractionPlan:
    return ExtractionPlan(
        run_id="run-1",
        doc_id="doc-1",
        domain_hints=("source-neutral",),
        approved_categories=(
            CategoryDefinition(
                name="Finding",
                description="A source-backed finding.",
                fields=(
                    FieldDefinition(
                        name="summary",
                        description="Short finding summary.",
                        value_type="text",
                        required=True,
                    ),
                    FieldDefinition(
                        name="response_window",
                        description="A source-backed response period.",
                        value_type="duration",
                        required=False,
                    ),
                ),
            ),
        ),
        enabled_lenses=("claim",),
        chunk_policy=ChunkPolicy(window_tokens=100, overlap_tokens=10),
        budget=ExtractionBudget(
            per_chunk_concurrency=1,
            lens_budgets=(LensBudget(lens="claim", max_calls=2),),
        ),
    )


def make_source_span(
    *,
    chunk_id: str,
    text: str,
    start_char: int,
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
    chunk_id: str,
    value: str,
    source_text: str,
    start_char: int,
    field_name: str = "summary",
    value_canonical: str | None = None,
    value_verbatim: str | None = None,
    value_kind: str = "text",
    normalization_status: str = "not_normalized",
) -> LensCandidate:
    return LensCandidate(
        candidate_id=candidate_id,
        run_id="run-1",
        doc_id="doc-1",
        chunk_id=chunk_id,
        lens="claim",
        category="Finding",
        field_name=field_name,
        value=value,
        source_span=make_source_span(
            chunk_id=chunk_id,
            text=source_text,
            start_char=start_char,
        ),
        confidence=0.82,
        executor_call_id=f"executor-{candidate_id}",
        value_verbatim=value_verbatim,
        value_canonical=value_canonical,
        value_kind=value_kind,
        normalization_status=normalization_status,
        normalization_policy_id=(
            "duration-key" if normalization_status == "canonicalized" else None
        ),
        normalization_policy_version=(
            "2026-05-29" if normalization_status == "canonicalized" else None
        ),
    )


def make_critic_report(candidate: LensCandidate) -> CriticReport:
    return CriticReport(
        report_id=f"critic-{candidate.candidate_id}",
        run_id="run-1",
        candidate_id=candidate.candidate_id,
        critic_call_id=f"critic-call-{candidate.candidate_id}",
        plausibility_score=0.9,
        accepted=True,
        issues=(),
    )


def make_verifier_report(candidate: LensCandidate) -> VerifierReport:
    return VerifierReport(
        report_id=f"verifier-{candidate.candidate_id}",
        run_id="run-1",
        candidate_id=candidate.candidate_id,
        verifier_call_id=f"verifier-call-{candidate.candidate_id}",
        span_verified=True,
        category_verified=True,
        alignment_score=0.91,
        accepted=True,
        rejection_reasons=(),
    )


def build_result(
    candidates: tuple[LensCandidate, ...],
    batch: ReconciliationBatch,
) -> tuple:
    return build_reconciliation_result(
        plan=make_plan(),
        candidates_by_id={candidate.candidate_id: candidate for candidate in candidates},
        critic_reports_by_candidate_id={
            candidate.candidate_id: make_critic_report(candidate) for candidate in candidates
        },
        verifier_reports_by_candidate_id={
            candidate.candidate_id: make_verifier_report(candidate)
            for candidate in candidates
        },
        batch=batch,
    )


def test_reconciled_group_populates_supporting_source_spans() -> None:
    primary = make_candidate(
        "candidate-a",
        chunk_id="chunk-1",
        value="Revenue increased",
        source_text="Revenue increased",
        start_char=0,
    )
    supporting = make_candidate(
        "candidate-b",
        chunk_id="chunk-2",
        value="Revenue increased",
        source_text="Revenue increased",
        start_char=40,
    )
    batch = ReconciliationBatch(
        groups=(("candidate-a", ("candidate-a", "candidate-b")),),
        rejected=(),
    )

    data_points, rejections = build_result((primary, supporting), batch)

    assert rejections == ()
    assert len(data_points) == 1
    assert data_points[0].source_span == primary.source_span
    assert data_points[0].supporting_source_spans == (
        primary.source_span,
        supporting.source_span,
    )


def test_same_field_distinct_canonical_values_are_marked_unresolved() -> None:
    first = make_candidate(
        "candidate-a",
        chunk_id="chunk-1",
        field_name="response_window",
        value="30 days",
        source_text="within thirty days",
        start_char=0,
        value_verbatim="within thirty days",
        value_canonical="30 days",
        value_kind="duration",
        normalization_status="canonicalized",
    )
    second = make_candidate(
        "candidate-b",
        chunk_id="chunk-2",
        field_name="response_window",
        value="45 days",
        source_text="within forty five days",
        start_char=60,
        value_verbatim="within forty five days",
        value_canonical="45 days",
        value_kind="duration",
        normalization_status="canonicalized",
    )
    batch = ReconciliationBatch(
        groups=(("candidate-a", ("candidate-a",)), ("candidate-b", ("candidate-b",))),
        rejected=(),
    )

    data_points, rejections = build_result((first, second), batch)

    assert rejections == ()
    assert len(data_points) == 2
    assert {data_point.value for data_point in data_points} == {"30 days", "45 days"}
    assert {data_point.conflict_status for data_point in data_points} == {"unresolved"}
    assert len({data_point.conflict_group_id for data_point in data_points}) == 1
    assert all(data_point.conflict_group_id for data_point in data_points)
    assert {data_point.conflict_reason for data_point in data_points} == {
        "same_field_distinct_canonical_values"
    }


def test_validation_complains_when_conflicting_candidate_is_omitted() -> None:
    first = make_candidate(
        "candidate-a",
        chunk_id="chunk-1",
        field_name="response_window",
        value="30 days",
        source_text="within thirty days",
        start_char=0,
        value_verbatim="within thirty days",
        value_canonical="30 days",
        value_kind="duration",
        normalization_status="canonicalized",
    )
    omitted_conflict = make_candidate(
        "candidate-b",
        chunk_id="chunk-2",
        field_name="response_window",
        value="45 days",
        source_text="within forty five days",
        start_char=60,
        value_verbatim="within forty five days",
        value_canonical="45 days",
        value_kind="duration",
        normalization_status="canonicalized",
    )
    _, candidates_by_view_id = build_candidate_view_map((first, omitted_conflict))
    batch = ReconciliationBatch(
        groups=((short_candidate_id("candidate-a"), (short_candidate_id("candidate-a"),)),),
        rejected=(),
    )

    validation = validate_reconciliation_batch(
        batch=batch,
        candidates_by_view_id=candidates_by_view_id,
    )

    assert isinstance(validation, Complaints)
    assert len(validation.complaints) == 1
    complaint = validation.complaints[0]
    assert complaint.identifier == short_candidate_id("candidate-b")
    assert "same-category/same-field" in complaint.message
    assert short_candidate_id("candidate-a") in complaint.message
