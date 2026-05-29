import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from extractor.audit import AuditStore, CandidateRejection, inspect_audit_database
from extractor.audit.cli import main as audit_main
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
STARTED = datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc)


def make_manifest() -> RunManifest:
    return RunManifest(
        run_id="run-1",
        doc_id="doc-1",
        audit_db_path="/tmp/audit.sqlite3",
        status="completed",
        started_at=STARTED,
        completed_at=datetime(2026, 4, 30, 12, 5, tzinfo=timezone.utc),
        output_data_point_ids=("dp-1",),
    )


def make_document() -> Document:
    return Document(
        doc_id="doc-1",
        source_path="/tmp/doc.txt",
        format="plain_text",
        text="hello world",
        source_sha256=HASH,
        text_sha256=HASH,
        source_byte_length=11,
        text_byte_length=11,
        page_map=(PageSpan(page_number=1, start_char=0, end_char=11, start_byte=0, end_byte=11),),
    )


def make_chunk() -> Chunk:
    return Chunk(
        chunk_id="chunk-1",
        doc_id="doc-1",
        chunk_index=0,
        text="hello world",
        start_char=0,
        end_char=11,
        start_byte=0,
        end_byte=11,
        start_token=0,
        end_token=2,
    )


def make_plan() -> ExtractionPlan:
    return ExtractionPlan(
        run_id="run-1",
        doc_id="doc-1",
        domain_hints=("test",),
        approved_categories=(
            CategoryDefinition(
                name="Finding",
                description="A finding.",
                fields=(
                    FieldDefinition(
                        name="summary",
                        description="Summary.",
                        value_type="text",
                        required=True,
                    ),
                ),
            ),
        ),
        enabled_lenses=("claim",),
        chunk_policy=ChunkPolicy(window_tokens=100, overlap_tokens=10),
        budget=ExtractionBudget(
            per_chunk_concurrency=1,
            lens_budgets=(LensBudget(lens="claim", max_calls=1),),
        ),
    )


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


def make_candidate(candidate_id: str) -> LensCandidate:
    return LensCandidate(
        candidate_id=candidate_id,
        run_id="run-1",
        doc_id="doc-1",
        chunk_id="chunk-1",
        lens="claim",
        category="Finding",
        field_name="summary",
        value="hello world",
        source_span=make_source_span(),
        confidence=0.8,
        executor_call_id=f"executor-{candidate_id}",
        value_verbatim="hello world",
        normalization_status="verbatim_only",
    )


def make_llm_call(
    call_id: str,
    stage: str,
    *,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int,
) -> LLMCallLog:
    return LLMCallLog(
        call_id=call_id,
        run_id="run-1",
        stage=stage,
        attempt=1,
        model="test-model",
        prompt_sha256=HASH,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_creation_tokens=3,
        latency_ms=12,
        stop_reason="tool_use",
        tool_name=f"{stage}-tool",
        created_at=STARTED,
    )


async def seed_audit_db(db_path: Path) -> None:
    first = make_candidate("candidate-1")
    duplicate = make_candidate("candidate-2")
    async with AuditStore(db_path) as store:
        await store.record_run_manifest(make_manifest())
        await store.record_document(make_document())
        await store.record_chunk(make_chunk())
        await store.record_extraction_plan(make_plan())
        for log in (
            make_llm_call("call-critic-1", "critic", input_tokens=100, output_tokens=20, cache_read_tokens=40),
            make_llm_call("call-critic-2", "critic", input_tokens=80, output_tokens=10, cache_read_tokens=20),
            make_llm_call("call-verifier-1", "verifier", input_tokens=70, output_tokens=8, cache_read_tokens=15),
        ):
            await store.record_llm_call_log(log)
        for candidate in (first, duplicate):
            await store.record_lens_candidate(candidate)
            await store.record_critic_report(
                CriticReport(
                    report_id=f"critic-{candidate.candidate_id}",
                    run_id="run-1",
                    candidate_id=candidate.candidate_id,
                    critic_call_id="call-critic-1",
                    plausibility_score=0.9,
                    accepted=True,
                    issues=(),
                )
            )
            await store.record_verifier_report(
                VerifierReport(
                    report_id=f"verifier-{candidate.candidate_id}",
                    run_id="run-1",
                    candidate_id=candidate.candidate_id,
                    verifier_call_id="call-verifier-1",
                    span_verified=True,
                    category_verified=True,
                    alignment_score=0.95,
                    accepted=True,
                    rejection_reasons=(),
                )
            )
        await store.record_candidate_rejection(
            CandidateRejection(
                rejection_id="rejection-dedup-1",
                run_id="run-1",
                candidate_id=duplicate.candidate_id,
                stage="dedup",
                reasons=(
                    RejectionReason(
                        code="duplicate_candidate",
                        message=f"merged_into:{first.candidate_id}",
                    ),
                ),
                created_at=STARTED,
            )
        )
        await store.record_data_point(
            DataPoint(
                data_point_id="dp-1",
                run_id="run-1",
                doc_id="doc-1",
                category="Finding",
                field_name="summary",
                value="hello world",
                source_span=make_source_span(),
                confidence=0.8,
                contributing_candidate_ids=("candidate-1", "candidate-2"),
                critic_report_ids=("critic-candidate-1", "critic-candidate-2"),
                verifier_report_ids=("verifier-candidate-1", "verifier-candidate-2"),
                reconciliation_decision_id="decision-1",
                supporting_source_spans=(make_source_span(),),
                conflict_status="unresolved",
                conflict_group_id="conflict-1",
                conflict_reason="same_field_distinct_canonical_values",
                value_verbatim="hello world",
                normalization_status="verbatim_only",
            )
        )


def test_inspect_audit_database_returns_acceptance_and_detail_summary(tmp_path: Path) -> None:
    async def run_check() -> None:
        db_path = tmp_path / "audit.sqlite3"
        await seed_audit_db(db_path)

        result = await inspect_audit_database(
            db_path,
            run_id="run-1",
            include_details=True,
        )

        assert result["run"]["run_id"] == "run-1"
        assert result["counts"]["candidates"] == {
            "total": 2,
            "dedup_duplicates": 1,
            "canonical_after_dedup": 1,
        }
        assert result["usage_summary"]["critic"]["calls"] == 2
        assert result["usage_summary"]["critic"]["cache_read_tokens"] == 60
        assert result["acceptance_checks"]["critic_batches_le_6"]["passed"] is True
        assert result["acceptance_checks"]["verifier_cache_read_tokens_nonzero"]["passed"] is True
        assert result["details"]["candidate_rejections"][0]["stage"] == "dedup"
        assert result["details"]["candidates"][0]["value_verbatim"] == "hello world"
        assert result["details"]["candidates"][0]["normalization_status"] == "verbatim_only"
        assert result["details"]["data_points"][0]["value_verbatim"] == "hello world"
        assert result["details"]["data_points"][0]["normalization_status"] == "verbatim_only"
        assert result["details"]["data_points"][0]["supporting_source_span_count"] == 1
        assert result["details"]["data_points"][0]["conflict_status"] == "unresolved"
        assert result["details"]["data_points"][0]["conflict_group_id"] == "conflict-1"
        assert (
            result["details"]["data_points"][0]["conflict_reason"]
            == "same_field_distinct_canonical_values"
        )
        assert result["details"]["data_points"][0]["contributing_candidate_ids"] == (
            "candidate-1",
            "candidate-2",
        )

    asyncio.run(run_check())


def test_audit_cli_prints_inspection_json(
    tmp_path: Path,
    capsys,
) -> None:
    db_path = tmp_path / "audit.sqlite3"
    asyncio.run(seed_audit_db(db_path))

    status = audit_main((str(db_path), "--run-id", "run-1"))

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert status == 0
    assert payload["run"]["run_id"] == "run-1"
    assert payload["counts"]["data_points"] == 1
    assert "details" not in payload
