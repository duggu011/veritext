import asyncio
from datetime import datetime, timezone
from pathlib import Path

import pytest

from extractor.audit import (
    AuditIntegrityError,
    AuditNotFoundError,
    AuditStore,
    CandidateRejection,
    RunStageState,
)
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
STARTED = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)


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


def make_plan() -> ExtractionPlan:
    return ExtractionPlan(
        run_id="run-1",
        doc_id="doc-1",
        domain_hints=("policy",),
        approved_categories=(
            CategoryDefinition(
                name="Finding",
                description="A domain-specific finding.",
                fields=(
                    FieldDefinition(
                        name="summary",
                        description="Short extracted value.",
                        value_type="text",
                        required=True,
                    ),
                ),
            ),
        ),
        enabled_lenses=("claim",),
        chunk_policy=ChunkPolicy(window_tokens=100, overlap_tokens=10),
        budget=ExtractionBudget(
            per_chunk_concurrency=2,
            lens_budgets=(LensBudget(lens="claim", max_calls=5),),
        ),
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


def make_manifest(status: str = "created") -> RunManifest:
    completed_at = datetime(2026, 4, 29, 10, 5, tzinfo=timezone.utc) if status == "completed" else None
    return RunManifest(
        run_id="run-1",
        doc_id="doc-1",
        audit_db_path="/tmp/audit.sqlite3",
        status=status,
        started_at=STARTED,
        completed_at=completed_at,
        output_data_point_ids=("dp-1",) if status == "completed" else (),
    )


def make_llm_call_log() -> LLMCallLog:
    return LLMCallLog(
        call_id="call-1",
        run_id="run-1",
        stage="executor.claim",
        attempt=1,
        model="configured-model",
        prompt_sha256=HASH,
        input_tokens=10,
        output_tokens=5,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        latency_ms=123,
        stop_reason="tool_use",
        tool_name="extract_claims",
        created_at=STARTED,
    )


def make_critic_report() -> CriticReport:
    return CriticReport(
        report_id="critic-1",
        run_id="run-1",
        candidate_id="candidate-1",
        critic_call_id="call-critic-1",
        plausibility_score=0.9,
        accepted=True,
        issues=(),
    )


def make_verifier_report() -> VerifierReport:
    return VerifierReport(
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


def make_data_point() -> DataPoint:
    return DataPoint(
        data_point_id="dp-1",
        run_id="run-1",
        doc_id="doc-1",
        category="Finding",
        field_name="summary",
        value="hello world",
        source_span=make_source_span(),
        confidence=0.9,
        contributing_candidate_ids=("candidate-1",),
        critic_report_ids=("critic-1",),
        verifier_report_ids=("verifier-1",),
        reconciliation_decision_id="decision-1",
    )


def make_rejection() -> CandidateRejection:
    return CandidateRejection(
        rejection_id="rejection-1",
        run_id="run-1",
        candidate_id="candidate-1",
        stage="verifier",
        reasons=(RejectionReason(code="invented_span", message="Span was not found."),),
        created_at=STARTED,
    )


def make_stage_state() -> RunStageState:
    return RunStageState(
        run_id="run-1",
        stage="planner",
        completed_at=STARTED,
    )


async def seed_provenance(store: AuditStore) -> None:
    await store.record_run_manifest(make_manifest())
    await store.record_document(make_document())
    await store.record_chunk(make_chunk())
    await store.record_extraction_plan(make_plan())


def test_audit_store_round_trips_contract_payloads(tmp_path: Path) -> None:
    async def run_check() -> None:
        db_path = tmp_path / "nested" / "audit.sqlite3"
        async with AuditStore(db_path) as store:
            await seed_provenance(store)
            await store.record_llm_call_log(make_llm_call_log())
            await store.record_lens_candidate(make_candidate())
            await store.record_critic_report(make_critic_report())
            await store.record_verifier_report(make_verifier_report())
            await store.record_data_point(make_data_point())

            assert db_path.exists()
            assert await store.get_run_manifest("run-1") == make_manifest()
            assert await store.get_document("doc-1") == make_document()
            assert await store.get_chunk("chunk-1") == make_chunk()
            assert await store.get_extraction_plan("run-1") == make_plan()
            assert await store.get_llm_call_log("call-1") == make_llm_call_log()
            assert await store.get_lens_candidate("candidate-1") == make_candidate()
            assert await store.get_critic_report("critic-1") == make_critic_report()
            assert await store.get_verifier_report("verifier-1") == make_verifier_report()
            assert await store.get_data_point("dp-1") == make_data_point()
            assert await store.list_chunks("doc-1") == (make_chunk(),)
            assert await store.list_llm_call_logs("run-1") == (make_llm_call_log(),)

    asyncio.run(run_check())


def test_audit_store_summarizes_run_usage_by_stage(tmp_path: Path) -> None:
    async def run_check() -> None:
        async with AuditStore(tmp_path / "audit.sqlite3") as store:
            await store.record_run_manifest(make_manifest())
            logs = (
                make_llm_call_log().model_copy(
                    update={
                        "call_id": "call-critic-1",
                        "stage": "critic",
                        "input_tokens": 100,
                        "output_tokens": 20,
                        "cache_read_tokens": 40,
                        "cache_creation_tokens": 5,
                    }
                ),
                make_llm_call_log().model_copy(
                    update={
                        "call_id": "call-critic-2",
                        "stage": "critic",
                        "input_tokens": 60,
                        "output_tokens": 15,
                        "cache_read_tokens": 10,
                        "cache_creation_tokens": 0,
                    }
                ),
                make_llm_call_log().model_copy(
                    update={
                        "call_id": "call-verifier-1",
                        "stage": "verifier",
                        "input_tokens": 30,
                        "output_tokens": 8,
                        "cache_read_tokens": 6,
                        "cache_creation_tokens": 2,
                    }
                ),
            )
            for log in logs:
                await store.record_llm_call_log(log)

            assert await store.summarize_run("run-1") == {
                "critic": {
                    "calls": 2,
                    "input_tokens": 160,
                    "output_tokens": 35,
                    "cache_read_tokens": 50,
                    "cache_creation_tokens": 5,
                },
                "verifier": {
                    "calls": 1,
                    "input_tokens": 30,
                    "output_tokens": 8,
                    "cache_read_tokens": 6,
                    "cache_creation_tokens": 2,
                },
            }
            assert await store.summarize_run("missing-run") == {}

    asyncio.run(run_check())


def test_audit_store_rejects_duplicate_audit_ids(tmp_path: Path) -> None:
    async def run_check() -> None:
        async with AuditStore(tmp_path / "audit.sqlite3") as store:
            await store.record_run_manifest(make_manifest())

            with pytest.raises(AuditIntegrityError):
                await store.record_run_manifest(make_manifest())

    asyncio.run(run_check())


def test_audit_store_idempotently_records_same_document_and_chunk(tmp_path: Path) -> None:
    async def run_check() -> None:
        async with AuditStore(tmp_path / "audit.sqlite3") as store:
            document = make_document()
            chunk = make_chunk()

            await store.record_document(document)
            await store.record_document(document)
            await store.record_chunk(chunk)
            await store.record_chunk(chunk)

            assert await store.get_document("doc-1") == document
            assert await store.list_chunks("doc-1") == (chunk,)

    asyncio.run(run_check())


def test_audit_store_rejects_conflicting_stable_document_or_chunk_ids(tmp_path: Path) -> None:
    async def run_check() -> None:
        async with AuditStore(tmp_path / "audit.sqlite3") as store:
            await store.record_document(make_document())
            conflicting_document = make_document().model_copy(update={"source_path": "/tmp/other.txt"})

            with pytest.raises(AuditIntegrityError):
                await store.record_document(conflicting_document)

            await store.record_chunk(make_chunk())
            conflicting_chunk = make_chunk().model_copy(update={"text": "HELLO world"})

            with pytest.raises(AuditIntegrityError):
                await store.record_chunk(conflicting_chunk)

    asyncio.run(run_check())


def test_audit_store_rejects_orphaned_provenance(tmp_path: Path) -> None:
    async def run_check() -> None:
        async with AuditStore(tmp_path / "audit.sqlite3") as store:
            with pytest.raises(AuditIntegrityError):
                await store.record_chunk(make_chunk())

            await store.record_document(make_document())

            with pytest.raises(AuditIntegrityError):
                await store.record_lens_candidate(make_candidate())

    asyncio.run(run_check())


def test_audit_store_updates_existing_run_manifest(tmp_path: Path) -> None:
    async def run_check() -> None:
        async with AuditStore(tmp_path / "audit.sqlite3") as store:
            await store.record_run_manifest(make_manifest())
            completed = make_manifest(status="completed")
            await store.update_run_manifest(completed)

            assert await store.get_run_manifest("run-1") == completed

            with pytest.raises(AuditNotFoundError):
                await store.update_run_manifest(completed.model_copy(update={"run_id": "missing-run"}))

    asyncio.run(run_check())


def test_audit_store_records_run_stage_state(tmp_path: Path) -> None:
    async def run_check() -> None:
        async with AuditStore(tmp_path / "audit.sqlite3") as store:
            await store.record_run_manifest(make_manifest())
            await store.record_run_stage_state(make_stage_state())

            assert await store.get_run_stage_state("run-1", "planner") == make_stage_state()
            assert await store.list_run_stage_states("run-1") == (make_stage_state(),)

            with pytest.raises(AuditIntegrityError):
                await store.record_run_stage_state(make_stage_state())

    asyncio.run(run_check())


def test_audit_store_logs_rejected_candidates_with_reasons(tmp_path: Path) -> None:
    async def run_check() -> None:
        async with AuditStore(tmp_path / "audit.sqlite3") as store:
            await seed_provenance(store)
            await store.record_lens_candidate(make_candidate())
            await store.record_candidate_rejection(make_rejection())

            assert await store.get_candidate_rejection("rejection-1") == make_rejection()
            assert await store.list_candidate_rejections("candidate-1") == (make_rejection(),)

    asyncio.run(run_check())
