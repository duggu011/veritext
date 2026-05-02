import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from extractor.audit import AuditStore
from extractor.config import LLMConfig
from extractor.contracts import (
    CategoryDefinition,
    Chunk,
    ChunkPolicy,
    CriticReport,
    Document,
    ExtractionBudget,
    ExtractionPlan,
    FieldDefinition,
    LensBudget,
    LensCandidate,
    PageSpan,
    RejectionReason,
    RunManifest,
    SourceSpan,
    VerifierReport,
)
from extractor.llm import LLMClient, PromptLoader
from extractor.llm.views import short_candidate_id
from extractor.reconciler import ReconcilerError, reconcile_candidates
from extractor.reconciler.models import ReconciliationBatch


ROOT = Path(__file__).resolve().parents[2]
HASH = "a" * 64
STARTED = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)


class QueuedMessages:
    def __init__(self, payloads: list[dict[str, object]]) -> None:
        self.payloads = payloads
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(
            content=[
                SimpleNamespace(
                    type="tool_use",
                    id=f"toolu_{len(self.calls)}",
                    name=kwargs["tool_choice"]["name"],
                    input=self.payloads.pop(0),
                )
            ],
            stop_reason="tool_use",
            usage=SimpleNamespace(
                input_tokens=50 + len(self.calls),
                output_tokens=13,
                cache_read_input_tokens=0,
                cache_creation_input_tokens=0,
            ),
        )


class QueuedAnthropicClient:
    def __init__(self, payloads: list[dict[str, object]]) -> None:
        self.messages = QueuedMessages(payloads)


def make_document() -> Document:
    text = "Revenue increased. Margin declined."
    text_bytes = text.encode("utf-8")
    return Document(
        doc_id="doc-1",
        source_path="/tmp/doc.txt",
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


def make_chunks() -> tuple[Chunk, ...]:
    document = make_document()
    split = document.text.index(" Margin")
    first = document.text[:split]
    second = document.text[split:]
    return (
        Chunk(
            chunk_id="chunk-1",
            doc_id=document.doc_id,
            chunk_index=0,
            text=first,
            start_char=0,
            end_char=len(first),
            start_byte=0,
            end_byte=len(first.encode("utf-8")),
            start_token=0,
            end_token=3,
        ),
        Chunk(
            chunk_id="chunk-2",
            doc_id=document.doc_id,
            chunk_index=1,
            text=second,
            start_char=split,
            end_char=len(document.text),
            start_byte=len(first.encode("utf-8")),
            end_byte=len(document.text.encode("utf-8")),
            start_token=2,
            end_token=5,
        ),
    )


def make_plan() -> ExtractionPlan:
    return ExtractionPlan(
        run_id="run-1",
        doc_id="doc-1",
        domain_hints=("finance",),
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


def make_run_manifest() -> RunManifest:
    return RunManifest(
        run_id="run-1",
        doc_id="doc-1",
        audit_db_path="/tmp/audit.sqlite3",
        status="created",
        started_at=STARTED,
        output_data_point_ids=(),
    )


def make_llm_config() -> LLMConfig:
    return LLMConfig(
        provider="anthropic",
        model="configured-model",
        max_retries=0,
        timeout_seconds=30,
        max_output_tokens=512,
        temperature=0.0,
    )


def make_candidate(
    *,
    candidate_id: str = "candidate-1",
    chunk: Chunk | None = None,
    source_text: str = "Revenue increased",
    start_char: int = 0,
    value: str = "Revenue increased",
) -> LensCandidate:
    actual_chunk = chunk or make_chunks()[0]
    start_byte = start_char
    return LensCandidate(
        candidate_id=candidate_id,
        run_id="run-1",
        doc_id="doc-1",
        chunk_id=actual_chunk.chunk_id,
        lens="claim",
        category="Finding",
        field_name="summary",
        value=value,
        source_span=SourceSpan(
            doc_id="doc-1",
            chunk_id=actual_chunk.chunk_id,
            start_char=start_char,
            end_char=start_char + len(source_text),
            start_byte=start_byte,
            end_byte=start_byte + len(source_text.encode("utf-8")),
            text=source_text,
        ),
        confidence=0.8,
        executor_call_id="call-executor-1",
    )


def make_critic_report(
    candidate: LensCandidate,
    *,
    corrected_candidate: LensCandidate | None = None,
) -> CriticReport:
    return CriticReport(
        report_id=f"critic-{candidate.candidate_id}",
        run_id="run-1",
        candidate_id=candidate.candidate_id,
        critic_call_id=f"call-critic-{candidate.candidate_id}",
        plausibility_score=0.9,
        accepted=True,
        issues=(),
        corrected_candidate=corrected_candidate,
    )


def make_verifier_report(candidate: LensCandidate) -> VerifierReport:
    return VerifierReport(
        report_id=f"verifier-{candidate.candidate_id}",
        run_id="run-1",
        candidate_id=candidate.candidate_id,
        verifier_call_id=f"call-verifier-{candidate.candidate_id}",
        span_verified=True,
        category_verified=True,
        alignment_score=0.92,
        accepted=True,
        rejection_reasons=(),
    )


def make_candidates() -> tuple[LensCandidate, LensCandidate]:
    chunks = make_chunks()
    second_start = make_document().text.index("Margin")
    return (
        make_candidate(candidate_id="candidate-1"),
        make_candidate(
            candidate_id="candidate-2",
            chunk=chunks[1],
            source_text="Margin declined",
            start_char=second_start,
            value="Margin declined",
        ),
    )


async def seed_audit_store(
    audit_store: AuditStore,
    candidates: tuple[LensCandidate, ...],
    critic_reports: tuple[CriticReport, ...],
    verifier_reports: tuple[VerifierReport, ...],
) -> None:
    await audit_store.record_run_manifest(make_run_manifest())
    document = make_document()
    await audit_store.record_document(document)
    for chunk in make_chunks():
        await audit_store.record_chunk(chunk)
    await audit_store.record_extraction_plan(make_plan())
    for candidate in candidates:
        await audit_store.record_lens_candidate(candidate)
    for report in critic_reports:
        await audit_store.record_critic_report(report)
    for report in verifier_reports:
        await audit_store.record_verifier_report(report)


def reconciliation_payload(
    *,
    rejected: tuple[tuple[str, str], ...] = (),
) -> dict[str, object]:
    first_id = short_candidate_id("candidate-1")
    return {
        "groups": ((first_id, (first_id,)),),
        "rejected": rejected,
    }


def test_reconciliation_batch_accepts_compact_group_shape() -> None:
    batch = ReconciliationBatch.model_validate(
        {
            "groups": (("abc123", ("abc123", "def456")),),
            "rejected": (("ghi789", "reconciler_rejected"),),
        }
    )

    assert batch.groups == (("abc123", ("abc123", "def456")),)
    assert batch.rejected == (("ghi789", "reconciler_rejected"),)


def test_reconciliation_batch_normalizes_short_compact_shapes() -> None:
    batch = ReconciliationBatch.model_validate(
        {
            "groups": json.dumps([["abc123", "abc123"]]),
            "rejected": [["def456"], "ghi789"],
        }
    )

    assert batch.groups == (("abc123", ("abc123",)),)
    assert batch.rejected == (
        ("def456", "reconciler_rejected"),
        ("ghi789", "reconciler_rejected"),
    )


def test_reconcile_candidates_persists_data_points_rejections_and_logs(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        candidates = make_candidates()
        critic_reports = tuple(make_critic_report(candidate) for candidate in candidates)
        verifier_reports = tuple(make_verifier_report(candidate) for candidate in candidates)
        anthropic_client = QueuedAnthropicClient(
            [
                reconciliation_payload(
                    rejected=(
                        (
                            short_candidate_id("candidate-2"),
                            "reconciler_rejected",
                        ),
                    ),
                )
            ]
        )
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store, candidates, critic_reports, verifier_reports)
            result = await reconcile_candidates(
                plan=make_plan(),
                candidates=candidates,
                critic_reports=critic_reports,
                verifier_reports=verifier_reports,
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                audit_store=audit_store,
            )
            stored_data_points = await audit_store.list_data_points("run-1")
            rejections = await audit_store.list_candidate_rejections("candidate-2")
            logs = await audit_store.list_llm_call_logs("run-1")

        assert result.data_points == stored_data_points
        assert result.rejections == rejections
        assert len(stored_data_points) == 1
        data_point = stored_data_points[0]
        assert data_point.value == "Revenue increased"
        assert data_point.source_span == candidates[0].source_span
        assert data_point.contributing_candidate_ids == ("candidate-1",)
        assert data_point.critic_report_ids == ("critic-candidate-1",)
        assert data_point.verifier_report_ids == ("verifier-candidate-1",)
        assert data_point.confidence == 0.8
        assert rejections[0].stage == "reconciler"
        assert rejections[0].reasons[0].code == "reconciler_rejected"
        assert rejections[0].reasons[0].message == "Reconciler rejected the candidate."
        assert [log.stage for log in logs] == ["reconciler"]
        assert anthropic_client.messages.calls[0]["tool_choice"] == {
            "type": "tool",
            "name": "reconcile_candidates",
        }
        user_content = anthropic_client.messages.calls[0]["messages"][0]["content"]
        user_payload = json.loads(user_content)
        assert set(user_payload) == {"schema_card", "candidates"}
        assert "critic_reports" not in user_payload
        assert "verifier_reports" not in user_payload
        assert "plan" not in user_payload
        assert "run_id" not in user_payload
        assert len(user_payload["candidates"]) == 2
        assert user_payload["candidates"][0]["id"] == short_candidate_id("candidate-1")
        assert "candidate_id" not in user_payload["candidates"][0]

    asyncio.run(run_check())


def test_reconcile_candidates_uses_accepted_corrected_candidate_without_rewriting(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        original = make_candidate(value="18%")
        corrected = original.model_copy(update={"value": "Approximately 18%"})
        critic_reports = (
            make_critic_report(original, corrected_candidate=corrected),
        )
        verifier_reports = (make_verifier_report(corrected),)
        anthropic_client = QueuedAnthropicClient([reconciliation_payload()])
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(
                audit_store,
                (corrected,),
                critic_reports,
                verifier_reports,
            )
            result = await reconcile_candidates(
                plan=make_plan(),
                candidates=(corrected,),
                critic_reports=critic_reports,
                verifier_reports=verifier_reports,
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                audit_store=audit_store,
            )

        assert len(result.data_points) == 1
        data_point = result.data_points[0]
        assert data_point.value == corrected.value
        assert data_point.source_span == corrected.source_span
        assert data_point.contributing_candidate_ids == (corrected.candidate_id,)

    asyncio.run(run_check())


def test_reconcile_candidates_prefers_tighter_source_candidate_in_group() -> None:
    async def run_check() -> None:
        chunk = Chunk(
            chunk_id="chunk-asset",
            doc_id="doc-1",
            chunk_index=0,
            text="Atacama-1 in Chile",
            start_char=0,
            end_char=len("Atacama-1 in Chile"),
            start_byte=0,
            end_byte=len("Atacama-1 in Chile".encode("utf-8")),
            start_token=0,
            end_token=4,
        )
        wide = make_candidate(
            candidate_id="candidate-wide",
            chunk=chunk,
            source_text="Atacama-1 in Chile",
            start_char=0,
            value="Atacama-1 in Chile",
        )
        narrow = make_candidate(
            candidate_id="candidate-narrow",
            chunk=chunk,
            source_text="Atacama-1",
            start_char=0,
            value="Atacama-1",
        )
        candidates = (wide, narrow)
        critic_reports = tuple(make_critic_report(candidate) for candidate in candidates)
        verifier_reports = tuple(make_verifier_report(candidate) for candidate in candidates)
        wide_id = short_candidate_id(wide.candidate_id)
        narrow_id = short_candidate_id(narrow.candidate_id)
        anthropic_client = QueuedAnthropicClient(
            [
                {
                    "groups": ((wide_id, (wide_id, narrow_id)),),
                    "rejected": (),
                }
            ]
        )
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        result = await reconcile_candidates(
            plan=make_plan(),
            candidates=candidates,
            critic_reports=critic_reports,
            verifier_reports=verifier_reports,
            prompt_loader=PromptLoader(ROOT / "prompts"),
            llm_client=llm_client,
        )

        assert len(result.data_points) == 1
        data_point = result.data_points[0]
        assert data_point.value == "Atacama-1"
        assert data_point.source_span == narrow.source_span
        assert data_point.contributing_candidate_ids == (
            "candidate-wide",
            "candidate-narrow",
        )

    asyncio.run(run_check())


def test_reconcile_candidates_logs_omitted_verified_candidates(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        candidates = make_candidates()
        critic_reports = tuple(make_critic_report(candidate) for candidate in candidates)
        verifier_reports = tuple(make_verifier_report(candidate) for candidate in candidates)
        anthropic_client = QueuedAnthropicClient([reconciliation_payload()])
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store, candidates, critic_reports, verifier_reports)
            result = await reconcile_candidates(
                plan=make_plan(),
                candidates=candidates,
                critic_reports=critic_reports,
                verifier_reports=verifier_reports,
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                audit_store=audit_store,
            )
            rejections = await audit_store.list_candidate_rejections("candidate-2")

        assert result.rejections == rejections
        assert rejections[0].stage == "reconciler"
        assert rejections[0].reasons == (
            RejectionReason(
                code="reconciler_rejected",
                message=(
                    "Candidate was not selected or explicitly rejected by "
                    "reconciliation output."
                ),
            ),
        )

    asyncio.run(run_check())


def test_reconcile_candidates_rejects_missing_verifier_report_before_llm_calls() -> None:
    async def run_check() -> None:
        candidates = (make_candidates()[0],)
        critic_reports = (make_critic_report(candidates[0]),)
        anthropic_client = QueuedAnthropicClient([])
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        with pytest.raises(ReconcilerError, match="accepted verifier report"):
            await reconcile_candidates(
                plan=make_plan(),
                candidates=candidates,
                critic_reports=critic_reports,
                verifier_reports=(),
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
            )

        assert anthropic_client.messages.calls == []

    asyncio.run(run_check())


def test_reconcile_candidates_rejects_unknown_output_candidate_id() -> None:
    async def run_check() -> None:
        candidates = (make_candidates()[0],)
        critic_reports = (make_critic_report(candidates[0]),)
        verifier_reports = (make_verifier_report(candidates[0]),)
        anthropic_client = QueuedAnthropicClient(
            [
                {
                    "groups": (("candidate-missing", ("candidate-missing",)),),
                    "rejected": (),
                }
            ]
        )
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        with pytest.raises(ReconcilerError, match="unknown candidate IDs"):
            await reconcile_candidates(
                plan=make_plan(),
                candidates=candidates,
                critic_reports=critic_reports,
                verifier_reports=verifier_reports,
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                max_retries=0,
            )

        assert len(anthropic_client.messages.calls) == 1

    asyncio.run(run_check())


def test_reconcile_candidates_retries_unknown_compact_candidate_id(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        candidates = make_candidates()
        critic_reports = tuple(make_critic_report(candidate) for candidate in candidates)
        verifier_reports = tuple(make_verifier_report(candidate) for candidate in candidates)
        good_first_id = short_candidate_id("candidate-1")
        good_second_id = short_candidate_id("candidate-2")
        anthropic_client = QueuedAnthropicClient(
            [
                {
                    "groups": (("6eb85b6df135", ("6eb85b6df135",)),),
                    "rejected": ((good_second_id, "reconciler_rejected"),),
                },
                {
                    "groups": ((good_first_id, (good_first_id,)),),
                    "rejected": ((good_second_id, "reconciler_rejected"),),
                },
            ]
        )
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store, candidates, critic_reports, verifier_reports)
            result = await reconcile_candidates(
                plan=make_plan(),
                candidates=candidates,
                critic_reports=critic_reports,
                verifier_reports=verifier_reports,
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                audit_store=audit_store,
                max_retries=1,
            )
            logs = await audit_store.list_llm_call_logs("run-1")

        assert len(anthropic_client.messages.calls) == 2
        assert [log.attempt for log in logs] == [1, 2]
        assert len(result.data_points) == 1
        assert result.data_points[0].contributing_candidate_ids == ("candidate-1",)
        retry_messages = anthropic_client.messages.calls[1]["messages"]
        assert len(retry_messages) == 3
        tool_result = retry_messages[2]["content"][0]
        assert tool_result["type"] == "tool_result"
        assert tool_result["is_error"] is True
        assert "6eb85b6df135" in tool_result["content"]
        assert good_first_id in tool_result["content"]

    asyncio.run(run_check())
