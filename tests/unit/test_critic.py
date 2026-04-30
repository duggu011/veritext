import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from extractor.audit import AuditStore
from extractor.config import ExecutionConfig, LLMConfig
from extractor.contracts import (
    CategoryDefinition,
    Chunk,
    ChunkPolicy,
    Document,
    ExtractionBudget,
    ExtractionPlan,
    FieldDefinition,
    LensBudget,
    LensCandidate,
    PageSpan,
    RunManifest,
    SourceSpan,
)
from extractor.critic import CriticError, review_candidates
from extractor.llm import LLMClient, PromptLoader, short_candidate_id


ROOT = Path(__file__).resolve().parents[2]
HASH = "a" * 64
STARTED = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)


class QueuedMessages:
    def __init__(self, payloads: list[dict[str, object]]) -> None:
        self.payloads = payloads
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        cache_read_tokens = 50 if len(self.calls) > 1 else 0
        return SimpleNamespace(
            content=[
                SimpleNamespace(
                    type="tool_use",
                    name=kwargs["tool_choice"]["name"],
                    input=self.payloads.pop(0),
                )
            ],
            stop_reason="tool_use",
            usage=SimpleNamespace(
                input_tokens=30 + len(self.calls),
                output_tokens=9,
                cache_read_input_tokens=cache_read_tokens,
                cache_creation_input_tokens=0,
            ),
        )


class QueuedAnthropicClient:
    def __init__(self, payloads: list[dict[str, object]]) -> None:
        self.messages = QueuedMessages(payloads)


def call_user_text(call: dict[str, object]) -> str:
    content = call["messages"][0]["content"]  # type: ignore[index]
    if isinstance(content, str):
        return content
    return "".join(str(block["text"]) for block in content)


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


def make_execution_config() -> ExecutionConfig:
    return ExecutionConfig(
        max_stage_concurrency=1,
        max_chunk_concurrency=1,
        max_llm_attempts=1,
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


async def seed_audit_store(
    audit_store: AuditStore,
    candidates: tuple[LensCandidate, ...],
) -> None:
    await audit_store.record_run_manifest(make_run_manifest())
    document = make_document()
    await audit_store.record_document(document)
    for chunk in make_chunks():
        await audit_store.record_chunk(chunk)
    await audit_store.record_extraction_plan(make_plan())
    for candidate in candidates:
        await audit_store.record_lens_candidate(candidate)


def accepted_payload(
    *,
    candidate_id: str,
    corrected_candidate: LensCandidate | None = None,
) -> dict[str, object]:
    if corrected_candidate is None:
        return {
            "id": short_candidate_id(candidate_id),
            "decision": "accept",
        }
    return {
        "id": short_candidate_id(candidate_id),
        "decision": "correct",
        "code": "schema_violation",
        "evidence": "Small correction makes the candidate source-faithful.",
        "correction": _raw_correction(corrected_candidate),
    }


def batch_payload(*items: dict[str, object]) -> dict[str, object]:
    return {"verdicts": tuple(items)}


def _raw_correction(candidate: LensCandidate | None) -> dict[str, object] | None:
    if candidate is None:
        return None
    return {
        "category": candidate.category,
        "field_name": candidate.field_name,
        "value": candidate.value,
        "source_start_char": candidate.source_span.start_char,
        "source_text": candidate.source_span.text,
    }


def rejected_payload(*, candidate_id: str) -> dict[str, object]:
    return {
        "id": short_candidate_id(candidate_id),
        "decision": "reject",
        "code": "critic_rejected",
        "evidence": "Value overstates the provided source evidence.",
    }


def test_review_candidates_persists_reports_rejections_and_logs(tmp_path: Path) -> None:
    async def run_check() -> None:
        chunks = make_chunks()
        second_start = make_document().text.index("Margin")
        candidates = (
            make_candidate(candidate_id="candidate-1"),
            make_candidate(
                candidate_id="candidate-2",
                chunk=chunks[1],
                source_text="Margin declined",
                start_char=second_start,
                value="Margin declined",
            ),
        )
        anthropic_client = QueuedAnthropicClient(
            [
                batch_payload(accepted_payload(candidate_id="candidate-1")),
                batch_payload(rejected_payload(candidate_id="candidate-2")),
            ]
        )
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store, candidates)
            result = await review_candidates(
                plan=make_plan(),
                chunks=chunks,
                candidates=candidates,
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                execution_config=make_execution_config(),
                audit_store=audit_store,
            )
            first_reports = await audit_store.list_critic_reports("candidate-1")
            second_reports = await audit_store.list_critic_reports("candidate-2")
            rejections = await audit_store.list_candidate_rejections("candidate-2")
            logs = await audit_store.list_llm_call_logs("run-1")

        assert result.accepted_candidates == (candidates[0],)
        assert result.rejected_candidates == (candidates[1],)
        assert result.reports == (*first_reports, *second_reports)
        assert result.rejections == rejections
        assert first_reports[0].accepted is True
        assert first_reports[0].plausibility_score == 1.0
        assert first_reports[0].issues == ()
        assert second_reports[0].accepted is False
        assert second_reports[0].plausibility_score == 0.0
        assert second_reports[0].issues[0].code == "critic_rejected"
        assert second_reports[0].issues[0].severity == "medium"
        assert second_reports[0].issues[0].message == (
            "Value overstates the provided source evidence."
        )
        assert rejections[0].stage == "critic"
        assert rejections[0].reasons[0].code == "critic_rejected"
        # Two chunks → two batches → two LLM calls (each batch carries one candidate).
        assert [log.stage for log in logs] == ["critic", "critic"]
        assert [call["tool_choice"] for call in anthropic_client.messages.calls] == [
            {"type": "tool", "name": "review_candidates_batch"},
            {"type": "tool", "name": "review_candidates_batch"},
        ]
        user_payload_text = call_user_text(anthropic_client.messages.calls[0])
        user_payload = json.loads(user_payload_text)
        assert user_payload["candidates"][0]["id"] == short_candidate_id("candidate-1")
        assert user_payload["chunk_view"] == {
            "start_char": 0,
            "text": "Revenue increased.",
        }
        for forbidden in (
            "candidate_id",
            "chunk_id",
            "doc_id",
            "run_id",
            "start_byte",
            "end_byte",
            "chunk_policy",
            "budget",
            "domain_hints",
            "executor_call_id",
        ):
            assert f'"{forbidden}"' not in user_payload_text

    asyncio.run(run_check())


def test_review_candidates_accepts_valid_correction(tmp_path: Path) -> None:
    async def run_check() -> None:
        candidate = make_candidate()
        corrected = candidate.model_copy(update={"value": "Revenue increased"})
        anthropic_client = QueuedAnthropicClient(
            [
                batch_payload(
                    accepted_payload(
                        candidate_id=candidate.candidate_id,
                        corrected_candidate=corrected,
                    )
                )
            ]
        )
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store, (candidate,))
            result = await review_candidates(
                plan=make_plan(),
                chunks=make_chunks(),
                candidates=(candidate,),
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                execution_config=make_execution_config(),
                audit_store=audit_store,
            )
            reports = await audit_store.list_critic_reports(candidate.candidate_id)

        assert result.accepted_candidates == (corrected,)
        assert result.rejected_candidates == ()
        assert reports[0].accepted is True
        assert reports[0].corrected_candidate == corrected

    asyncio.run(run_check())


def test_review_candidates_rejects_invalid_correction_without_silent_drop(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        candidate = make_candidate()
        bad_start = make_document().text.index("Margin")
        bad_span = SourceSpan(
            doc_id="doc-1",
            chunk_id="chunk-1",
            start_char=bad_start,
            end_char=bad_start + len("Revenue increased"),
            start_byte=bad_start,
            end_byte=bad_start + len("Revenue increased".encode("utf-8")),
            text="Revenue increased",
        )
        corrected = candidate.model_copy(update={"source_span": bad_span})
        anthropic_client = QueuedAnthropicClient(
            [
                batch_payload(
                    accepted_payload(
                        candidate_id=candidate.candidate_id,
                        corrected_candidate=corrected,
                    )
                )
            ]
        )
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store, (candidate,))
            result = await review_candidates(
                plan=make_plan(),
                chunks=make_chunks(),
                candidates=(candidate,),
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                execution_config=make_execution_config(),
                audit_store=audit_store,
            )
            reports = await audit_store.list_critic_reports(candidate.candidate_id)
            rejections = await audit_store.list_candidate_rejections(candidate.candidate_id)

        assert result.accepted_candidates == ()
        assert result.rejected_candidates == (candidate,)
        assert reports[0].accepted is False
        assert reports[0].corrected_candidate is None
        assert reports[0].issues[-1].code == "invalid_correction"
        assert rejections[0].stage == "critic"
        assert rejections[0].reasons[0].code == "invented_span"

    asyncio.run(run_check())


def test_review_candidates_survives_malformed_correction_offsets(tmp_path: Path) -> None:
    async def run_check() -> None:
        candidate = make_candidate()
        # The critic claims source_text is "Margin declined" at the original
        # candidate's start_char (which actually points at "Revenue increased").
        # The chunk-slice check must catch this and surface a typed rejection
        # instead of letting Pydantic crash the run.
        bad_correction = _raw_correction(candidate) or {}
        bad_correction["source_start_char"] = candidate.source_span.start_char
        bad_correction["source_text"] = "Margin declined"
        item = {
            "id": short_candidate_id(candidate.candidate_id),
            "decision": "correct",
            "code": "schema_violation",
            "evidence": "Correction should fail span validation.",
            "correction": bad_correction,
        }
        anthropic_client = QueuedAnthropicClient([batch_payload(item)])
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store, (candidate,))
            result = await review_candidates(
                plan=make_plan(),
                chunks=make_chunks(),
                candidates=(candidate,),
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                execution_config=make_execution_config(),
                audit_store=audit_store,
            )
            reports = await audit_store.list_critic_reports(candidate.candidate_id)
            rejections = await audit_store.list_candidate_rejections(candidate.candidate_id)

        assert result.accepted_candidates == ()
        assert result.rejected_candidates == (candidate,)
        assert reports[0].accepted is False
        assert reports[0].corrected_candidate is None
        assert reports[0].issues[-1].code == "invalid_correction"
        assert rejections[0].reasons[0].code == "invented_span"
        # Either the chunk-slice pre-check or the strict re-validation may fire,
        # depending on the failure shape. Both indicate a rejected correction.
        assert (
            "does not match the chunk slice" in rejections[0].reasons[0].message
            or "violated invariants" in rejections[0].reasons[0].message
        )

    asyncio.run(run_check())


def test_review_candidates_batches_per_chunk(tmp_path: Path) -> None:
    async def run_check() -> None:
        chunks = make_chunks()
        margin_start = make_document().text.index("Margin")
        chunk1_candidates = tuple(
            make_candidate(candidate_id=f"chunk1-cand-{i}") for i in range(8)
        )
        chunk2_candidates = tuple(
            make_candidate(
                candidate_id=f"chunk2-cand-{i}",
                chunk=chunks[1],
                source_text="Margin declined",
                start_char=margin_start,
                value="Margin declined",
            )
            for i in range(4)
        )
        candidates = chunk1_candidates + chunk2_candidates

        # critic_batch_size=5 → chunk-1 (8) splits into 5+3, chunk-2 (4) is one batch.
        # Total: 3 LLM calls, regardless of candidate count.
        anthropic_client = QueuedAnthropicClient(
            [
                batch_payload(
                    *[accepted_payload(candidate_id=c.candidate_id) for c in chunk1_candidates[:5]]
                ),
                batch_payload(
                    *[accepted_payload(candidate_id=c.candidate_id) for c in chunk1_candidates[5:]]
                ),
                batch_payload(
                    *[accepted_payload(candidate_id=c.candidate_id) for c in chunk2_candidates]
                ),
            ]
        )
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)
        execution_config = ExecutionConfig(
            max_stage_concurrency=1,
            max_chunk_concurrency=1,
            max_llm_attempts=1,
            critic_batch_size=5,
        )

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store, candidates)
            result = await review_candidates(
                plan=make_plan(),
                chunks=chunks,
                candidates=candidates,
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                execution_config=execution_config,
                audit_store=audit_store,
            )
            logs = await audit_store.list_llm_call_logs("run-1")

        assert len(logs) == 3
        assert all(log.stage == "critic" for log in logs)
        assert logs[0].cache_read_tokens == 0
        assert all(log.cache_read_tokens > 0 for log in logs[1:])
        assert len(result.accepted_candidates) == 12
        assert result.rejected_candidates == ()
        assert len(result.reports) == 12
        assert {report.candidate_id for report in result.reports} == {
            c.candidate_id for c in candidates
        }
        assert all(
            call["tool_choice"]["name"] == "review_candidates_batch"
            for call in anthropic_client.messages.calls
        )

    asyncio.run(run_check())


def test_review_candidates_rejects_candidate_plan_mismatch_before_llm_calls() -> None:
    async def run_check() -> None:
        candidate = make_candidate().model_copy(update={"run_id": "run-2"})
        anthropic_client = QueuedAnthropicClient([])
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        with pytest.raises(CriticError, match="candidate run_id must match"):
            await review_candidates(
                plan=make_plan(),
                chunks=make_chunks(),
                candidates=(candidate,),
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                execution_config=make_execution_config(),
            )

        assert anthropic_client.messages.calls == []

    asyncio.run(run_check())
