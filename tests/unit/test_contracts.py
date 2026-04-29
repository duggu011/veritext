from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from extractor.contracts import (
    CategoryDefinition,
    Chunk,
    ChunkPolicy,
    CriticReport,
    DataPoint,
    Document,
    ExtractionBudget,
    ExtractionPlan,
    FieldDefinition,
    LLMCallLog,
    LensBudget,
    LensCandidate,
    PageSpan,
    RejectionReason,
    RunManifest,
    SourceSpan,
    VerifierReport,
)


HASH = "a" * 64


def make_source_span() -> SourceSpan:
    return SourceSpan(
        doc_id="doc-1",
        chunk_id="chunk-1",
        start_char=0,
        end_char=11,
        start_byte=0,
        end_byte=11,
        text="hello world",
    )


def make_candidate() -> LensCandidate:
    return LensCandidate(
        candidate_id="candidate-1",
        run_id="run-1",
        doc_id="doc-1",
        chunk_id="chunk-1",
        lens="claim",
        category="Finding",
        field_name="summary",
        value="hello world",
        source_span=make_source_span(),
        confidence=0.8,
        executor_call_id="call-executor-1",
    )


def make_category(name: str = "Finding") -> CategoryDefinition:
    return CategoryDefinition(
        name=name,
        description="A domain-specific finding.",
        fields=(
            FieldDefinition(
                name="summary",
                description="Short extracted value.",
                value_type="text",
                required=True,
            ),
        ),
    )


def test_document_rejects_extra_fields_and_invalid_page_map() -> None:
    with pytest.raises(ValidationError):
        Document(
            doc_id="doc-1",
            source_path="/tmp/doc.txt",
            format="plain_text",
            text="abc",
            source_sha256=HASH,
            text_sha256=HASH,
            source_byte_length=3,
            text_byte_length=3,
            page_map=(PageSpan(page_number=1, start_char=0, end_char=4, start_byte=0, end_byte=4),),
            extra_field="not allowed",
        )


def test_document_tracks_text_bytes_and_page_offsets() -> None:
    document = Document(
        doc_id="doc-1",
        source_path="/tmp/doc.txt",
        format="plain_text",
        text="é",
        source_sha256=HASH,
        text_sha256=HASH,
        source_byte_length=2,
        text_byte_length=2,
        page_map=(PageSpan(page_number=1, start_char=0, end_char=1, start_byte=0, end_byte=2),),
    )

    assert document.text_byte_length == 2

    with pytest.raises(ValidationError):
        Document(
            doc_id="doc-1",
            source_path="/tmp/doc.txt",
            format="plain_text",
            text="é",
            source_sha256=HASH,
            text_sha256=HASH,
            source_byte_length=2,
            text_byte_length=1,
            page_map=(PageSpan(page_number=1, start_char=0, end_char=1, start_byte=0, end_byte=1),),
        )


def test_strict_offsets_reject_string_numbers() -> None:
    with pytest.raises(ValidationError):
        SourceSpan(
            doc_id="doc-1",
            chunk_id="chunk-1",
            start_char="0",
            end_char=4,
            start_byte=0,
            end_byte=4,
            text="text",
        )


def test_identifiers_reject_whitespace_only_values() -> None:
    with pytest.raises(ValidationError):
        SourceSpan(
            doc_id=" ",
            chunk_id="chunk-1",
            start_char=0,
            end_char=4,
            start_byte=0,
            end_byte=4,
            text="text",
        )


def test_source_span_text_must_match_offsets() -> None:
    with pytest.raises(ValidationError):
        SourceSpan(
            doc_id="doc-1",
            chunk_id="chunk-1",
            start_char=0,
            end_char=10,
            start_byte=0,
            end_byte=5,
            text="short",
        )


def test_chunk_requires_ordered_offsets_and_matching_text_length() -> None:
    chunk = Chunk(
        chunk_id="chunk-1",
        doc_id="doc-1",
        chunk_index=0,
        text="hello",
        start_char=3,
        end_char=8,
        start_byte=3,
        end_byte=8,
        start_token=1,
        end_token=3,
    )

    assert chunk.text == "hello"

    with pytest.raises(ValidationError):
        Chunk(
            chunk_id="chunk-2",
            doc_id="doc-1",
            chunk_index=1,
            text="hello",
            start_char=3,
            end_char=7,
            start_byte=3,
            end_byte=8,
            start_token=2,
            end_token=2,
        )


def test_extraction_plan_enforces_unique_categories_and_lens_budgets() -> None:
    valid_plan = ExtractionPlan(
        run_id="run-1",
        doc_id="doc-1",
        domain_hints=("policy",),
        approved_categories=(make_category("Finding"),),
        enabled_lenses=("claim",),
        chunk_policy=ChunkPolicy(window_tokens=100, overlap_tokens=10),
        budget=ExtractionBudget(
            per_chunk_concurrency=2,
            lens_budgets=(LensBudget(lens="claim", max_calls=5),),
        ),
    )

    assert valid_plan.approved_category_names == frozenset({"Finding"})

    with pytest.raises(ValidationError):
        ExtractionPlan(
            run_id="run-1",
            doc_id="doc-1",
            domain_hints=(),
            approved_categories=(make_category("Finding"), make_category("Finding")),
            enabled_lenses=("claim",),
            chunk_policy=ChunkPolicy(window_tokens=100, overlap_tokens=10),
            budget=ExtractionBudget(
                per_chunk_concurrency=2,
                lens_budgets=(LensBudget(lens="claim", max_calls=5),),
            ),
        )

    with pytest.raises(ValidationError):
        ExtractionPlan(
            run_id="run-1",
            doc_id="doc-1",
            domain_hints=(),
            approved_categories=(make_category("Finding"),),
            enabled_lenses=("claim", "number"),
            chunk_policy=ChunkPolicy(window_tokens=100, overlap_tokens=10),
            budget=ExtractionBudget(
                per_chunk_concurrency=2,
                lens_budgets=(LensBudget(lens="claim", max_calls=5),),
            ),
        )


def test_confidence_required_and_bounded_for_data_points() -> None:
    valid_payload = {
        "data_point_id": "dp-1",
        "run_id": "run-1",
        "doc_id": "doc-1",
        "category": "Finding",
        "field_name": "summary",
        "value": "hello world",
        "source_span": make_source_span(),
        "confidence": 0.9,
        "contributing_candidate_ids": ("candidate-1",),
        "critic_report_ids": ("critic-1",),
        "verifier_report_ids": ("verifier-1",),
        "reconciliation_decision_id": "decision-1",
    }

    assert DataPoint(**valid_payload).confidence == 0.9

    missing_confidence = dict(valid_payload)
    del missing_confidence["confidence"]
    with pytest.raises(ValidationError):
        DataPoint(**missing_confidence)

    out_of_range_confidence = dict(valid_payload)
    out_of_range_confidence["confidence"] = 1.1
    with pytest.raises(ValidationError):
        DataPoint(**out_of_range_confidence)


def test_candidate_and_data_point_source_identity_must_match() -> None:
    bad_span = SourceSpan(
        doc_id="doc-2",
        chunk_id="chunk-1",
        start_char=0,
        end_char=4,
        start_byte=0,
        end_byte=4,
        text="text",
    )

    with pytest.raises(ValidationError):
        LensCandidate(
            candidate_id="candidate-1",
            run_id="run-1",
            doc_id="doc-1",
            chunk_id="chunk-1",
            lens="entity",
            category="Finding",
            field_name="summary",
            value="text",
            source_span=bad_span,
            confidence=0.5,
            executor_call_id="call-executor-1",
        )


def test_critic_correction_preserves_candidate_identity() -> None:
    candidate = make_candidate()
    corrected = candidate.model_copy(update={"candidate_id": "candidate-2"})

    with pytest.raises(ValidationError):
        CriticReport(
            report_id="critic-1",
            run_id="run-1",
            candidate_id="candidate-1",
            critic_call_id="call-critic-1",
            plausibility_score=0.4,
            accepted=False,
            issues=(),
            corrected_candidate=corrected,
        )


def test_verifier_report_rejection_reasons_match_acceptance() -> None:
    accepted = VerifierReport(
        report_id="verifier-1",
        run_id="run-1",
        candidate_id="candidate-1",
        verifier_call_id="call-verifier-1",
        span_verified=True,
        category_verified=True,
        alignment_score=0.95,
        accepted=True,
        rejection_reasons=(),
    )

    assert accepted.accepted is True

    with pytest.raises(ValidationError):
        VerifierReport(
            report_id="verifier-2",
            run_id="run-1",
            candidate_id="candidate-1",
            verifier_call_id="call-verifier-1",
            span_verified=False,
            category_verified=True,
            alignment_score=0.2,
            accepted=False,
            rejection_reasons=(),
        )

    with pytest.raises(ValidationError):
        VerifierReport(
            report_id="verifier-3",
            run_id="run-1",
            candidate_id="candidate-1",
            verifier_call_id="call-verifier-1",
            span_verified=True,
            category_verified=True,
            alignment_score=0.9,
            accepted=True,
            rejection_reasons=(
                RejectionReason(code="invented_span", message="Span was not found."),
            ),
        )


def test_run_manifest_requires_valid_completion_time() -> None:
    started = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)

    with pytest.raises(ValidationError):
        RunManifest(
            run_id="run-1",
            doc_id="doc-1",
            audit_db_path="/tmp/run.db",
            status="completed",
            started_at=started,
            completed_at=None,
            output_data_point_ids=(),
        )

    with pytest.raises(ValidationError):
        RunManifest(
            run_id="run-1",
            doc_id="doc-1",
            audit_db_path="/tmp/run.db",
            status="failed",
            started_at=started,
            completed_at=datetime(2026, 4, 29, 9, 0, tzinfo=timezone.utc),
            output_data_point_ids=(),
        )


def test_llm_call_log_validates_prompt_hash_and_metrics() -> None:
    log = LLMCallLog(
        call_id="call-1",
        run_id="run-1",
        stage="executor.claim",
        attempt=1,
        model="configured-model",
        prompt_sha256=HASH,
        input_tokens=10,
        output_tokens=5,
        cache_read_tokens=3,
        cache_creation_tokens=2,
        latency_ms=123,
        stop_reason="tool_use",
        tool_name="extract_claims",
        created_at=datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc),
    )

    assert log.input_tokens == 10

    with pytest.raises(ValidationError):
        LLMCallLog(
            call_id="call-1",
            run_id="run-1",
            stage="executor.claim",
            attempt=0,
            model="configured-model",
            prompt_sha256="not-a-hash",
            input_tokens=-1,
            output_tokens=5,
            cache_read_tokens=3,
            cache_creation_tokens=2,
            latency_ms=123,
            stop_reason="tool_use",
            tool_name="extract_claims",
            created_at=datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc),
        )
