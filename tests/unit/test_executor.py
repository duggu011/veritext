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
    PageSpan,
    RunManifest,
)
from extractor.executor import ExecutorError, execute_plan
from extractor.llm import LLMClient, PromptLoader


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
                    name=kwargs["tool_choice"]["name"],
                    input=self.payloads.pop(0),
                )
            ],
            stop_reason="tool_use",
            usage=SimpleNamespace(
                input_tokens=20 + len(self.calls),
                output_tokens=7,
                cache_read_input_tokens=0,
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


def make_plan(max_calls: int = 2) -> ExtractionPlan:
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
            lens_budgets=(LensBudget(lens="claim", max_calls=max_calls),),
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


def candidate_payload(
    *,
    category: str = "Finding",
    field_name: str = "summary",
    source_text: str = "Revenue increased",
    source_length: int | None = None,
    start_char: int = 0,
    value: str = "Revenue increased",
) -> dict[str, object]:
    return {
        "category": category,
        "field_name": field_name,
        "value": value,
        "source_length": len(source_text) if source_length is None else source_length,
        "start_char": start_char,
        "confidence": 0.9,
    }


async def seed_audit_store(audit_store: AuditStore) -> None:
    await audit_store.record_run_manifest(make_run_manifest())
    document = make_document()
    await audit_store.record_document(document)
    for chunk in make_chunks():
        await audit_store.record_chunk(chunk)
    await audit_store.record_extraction_plan(make_plan())


def test_execute_plan_persists_accepted_and_rejected_candidates(tmp_path: Path) -> None:
    async def run_check() -> None:
        second_start = make_document().text.index("Margin")
        payloads = [
            {"candidates": (candidate_payload(),)},
            {
                "candidates": (
                    candidate_payload(
                        category="Unsupported",
                        source_text="Margin declined",
                        start_char=second_start,
                        value="Margin declined",
                    ),
                )
            },
        ]
        anthropic_client = QueuedAnthropicClient(payloads)
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store)
            result = await execute_plan(
                plan=make_plan(),
                chunks=make_chunks(),
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                execution_config=make_execution_config(),
                audit_store=audit_store,
            )
            stored_candidates = await audit_store.list_lens_candidates("run-1")
            rejections = await audit_store.list_candidate_rejections(
                result.rejected_candidates[0].candidate_id
            )
            logs = await audit_store.list_llm_call_logs("run-1")

        assert len(result.accepted_candidates) == 1
        assert len(result.rejected_candidates) == 1
        assert result.rejections == rejections
        assert len(stored_candidates) == 2
        assert result.accepted_candidates[0] in stored_candidates
        assert result.rejected_candidates[0] in stored_candidates
        assert rejections[0].stage == "executor"
        assert rejections[0].reasons[0].code == "category_not_approved"
        assert [log.stage for log in logs] == ["executor.claim", "executor.claim"]
        assert [call["tool_choice"] for call in anthropic_client.messages.calls] == [
            {"type": "tool", "name": "extract_claim_candidates"},
            {"type": "tool", "name": "extract_claim_candidates"},
        ]
        first_payload_text = call_user_text(anthropic_client.messages.calls[0])
        first_content = anthropic_client.messages.calls[0]["messages"][0]["content"]
        assert isinstance(first_content, list)
        assert first_content[0]["cache_control"] == {"type": "ephemeral"}
        assert str(first_content[0]["text"]).endswith('"chunk_view":')
        assert '"Revenue increased."' not in str(first_content[0]["text"])
        first_payload = json.loads(first_payload_text)
        assert first_payload["chunk_view"] == {
            "start_char": 0,
            "text": "Revenue increased.",
        }
        assert first_payload["schema_card"]["enabled_lenses"] == ["claim"]
        for forbidden in (
            "chunk_id",
            "doc_id",
            "run_id",
            "start_byte",
            "end_byte",
            "chunk_policy",
            "budget",
            "domain_hints",
        ):
            assert f'"{forbidden}"' not in first_payload_text

    asyncio.run(run_check())


def test_execute_plan_does_not_cache_single_chunk_executor_prompt() -> None:
    async def run_check() -> None:
        anthropic_client = QueuedAnthropicClient([{"candidates": (candidate_payload(),)}])
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        await execute_plan(
            plan=make_plan(max_calls=1),
            chunks=(make_chunks()[0],),
            prompt_loader=PromptLoader(ROOT / "prompts"),
            llm_client=llm_client,
            execution_config=make_execution_config(),
        )

        call = anthropic_client.messages.calls[0]
        assert isinstance(call["system"], str)
        assert isinstance(call["messages"][0]["content"], str)  # type: ignore[index]
        assert "cache_control" not in call["tools"][0]

    asyncio.run(run_check())


def test_execute_plan_accepts_semantic_value_backed_by_source_span(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        start = make_document().text.index("Margin")
        payloads = [
            {
                "candidates": (
                    candidate_payload(
                        source_text="Margin declined",
                        start_char=start,
                        value="Performance decline",
                    ),
                )
            }
        ]
        llm_client = LLMClient(
            make_llm_config(),
            anthropic_client=QueuedAnthropicClient(payloads),
        )

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store)
            result = await execute_plan(
                plan=make_plan(max_calls=1),
                chunks=(make_chunks()[1],),
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                execution_config=make_execution_config(),
                audit_store=audit_store,
            )
            stored_candidates = await audit_store.list_lens_candidates("run-1")

        assert len(result.accepted_candidates) == 1
        assert result.rejected_candidates == ()
        assert len(stored_candidates) == 1
        assert result.accepted_candidates[0].value == "Performance decline"
        assert result.accepted_candidates[0].source_span.text == "Margin declined"

    asyncio.run(run_check())


def test_execute_plan_auto_corrects_off_by_one_offsets(tmp_path: Path) -> None:
    async def run_check() -> None:
        # Chunk 1 starts with a leading space (" Margin declined."), so
        # "Margin declined" is one character past the chunk start. A model that
        # points to the leading whitespace is off-by-one; the validator should
        # locate the unique value span and auto-correct.
        chunk = make_chunks()[1]
        true_start = chunk.start_char + chunk.text.index("Margin declined")
        off_by_one_payload = candidate_payload(
            source_text="Margin declined",
            start_char=true_start - 1,
            value="Margin declined",
        )
        llm_client = LLMClient(
            make_llm_config(),
            anthropic_client=QueuedAnthropicClient([{"candidates": (off_by_one_payload,)}]),
        )

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store)
            result = await execute_plan(
                plan=make_plan(max_calls=1),
                chunks=(chunk,),
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                execution_config=make_execution_config(),
                audit_store=audit_store,
            )

        assert len(result.accepted_candidates) == 1
        assert result.rejected_candidates == ()
        accepted = result.accepted_candidates[0]
        assert accepted.source_span.start_char == true_start
        assert accepted.source_span.text == "Margin declined"

    asyncio.run(run_check())


def test_execute_plan_auto_corrects_far_off_unique_offsets() -> None:
    async def run_check() -> None:
        chunk_text = (
            "Intro sentence with unrelated context. "
            "More unrelated context before the real value. "
            "Fleet generation"
        )
        chunk = Chunk(
            chunk_id="chunk-far",
            doc_id="doc-1",
            chunk_index=0,
            text=chunk_text,
            start_char=0,
            end_char=len(chunk_text),
            start_byte=0,
            end_byte=len(chunk_text.encode("utf-8")),
            start_token=0,
            end_token=20,
        )
        true_start = chunk_text.index("Fleet generation")
        payload = candidate_payload(
            source_text="Fleet generation",
            start_char=0,
            value="Fleet generation",
        )
        llm_client = LLMClient(
            make_llm_config(),
            anthropic_client=QueuedAnthropicClient([{"candidates": (payload,)}]),
        )

        result = await execute_plan(
            plan=make_plan(max_calls=1),
            chunks=(chunk,),
            prompt_loader=PromptLoader(ROOT / "prompts"),
            llm_client=llm_client,
            execution_config=make_execution_config(),
        )

        assert len(result.accepted_candidates) == 1
        assert result.rejected_candidates == ()
        assert result.accepted_candidates[0].source_span.start_char == true_start

    asyncio.run(run_check())


def test_execute_plan_rejects_far_off_ambiguous_offsets() -> None:
    async def run_check() -> None:
        chunk_text = "Q1 2026 revenue increased. Q1 2026 guidance reaffirmed."
        chunk = Chunk(
            chunk_id="chunk-ambiguous",
            doc_id="doc-1",
            chunk_index=0,
            text=chunk_text,
            start_char=0,
            end_char=len(chunk_text),
            start_byte=0,
            end_byte=len(chunk_text.encode("utf-8")),
            start_token=0,
            end_token=12,
        )
        payload = candidate_payload(
            source_text="Q1 2026",
            start_char=5,
            value="Q1 2026",
        )
        llm_client = LLMClient(
            make_llm_config(),
            anthropic_client=QueuedAnthropicClient([{"candidates": (payload,)}]),
        )

        result = await execute_plan(
            plan=make_plan(max_calls=1),
            chunks=(chunk,),
            prompt_loader=PromptLoader(ROOT / "prompts"),
            llm_client=llm_client,
            execution_config=make_execution_config(),
        )

        assert result.accepted_candidates == ()
        assert len(result.rejected_candidates) == 1
        assert {reason.code for reason in result.rejections[0].reasons} == {
            "invalid_source_offsets",
            "ambiguous_source_span",
        }

    asyncio.run(run_check())


def test_execute_plan_rejects_claimed_exact_short_ambiguous_span() -> None:
    async def run_check() -> None:
        chunk_text = "Q1 2026 revenue increased. Q1 2026 guidance reaffirmed."
        chunk = Chunk(
            chunk_id="chunk-ambiguous-exact",
            doc_id="doc-1",
            chunk_index=0,
            text=chunk_text,
            start_char=0,
            end_char=len(chunk_text),
            start_byte=0,
            end_byte=len(chunk_text.encode("utf-8")),
            start_token=0,
            end_token=12,
        )
        payload = candidate_payload(
            source_text="Q1 2026",
            start_char=0,
            value="Q1 2026",
        )
        llm_client = LLMClient(
            make_llm_config(),
            anthropic_client=QueuedAnthropicClient([{"candidates": (payload,)}]),
        )

        result = await execute_plan(
            plan=make_plan(max_calls=1),
            chunks=(chunk,),
            prompt_loader=PromptLoader(ROOT / "prompts"),
            llm_client=llm_client,
            execution_config=make_execution_config(),
        )

        assert result.accepted_candidates == ()
        assert len(result.rejected_candidates) == 1
        assert result.rejections[0].reasons[0].code == "ambiguous_source_span"

    asyncio.run(run_check())


def test_execute_plan_auto_corrects_unique_whitespace_normalized_span() -> None:
    async def run_check() -> None:
        chunk_text = (
            "Full-year 2026 revenue\n"
            "guidance reaffirmed at $2.10 to $2.25 billion."
        )
        chunk = Chunk(
            chunk_id="chunk-whitespace",
            doc_id="doc-1",
            chunk_index=0,
            text=chunk_text,
            start_char=0,
            end_char=len(chunk_text),
            start_byte=0,
            end_byte=len(chunk_text.encode("utf-8")),
            start_token=0,
            end_token=14,
        )
        payload = candidate_payload(
            source_text=(
                "Full-year 2026 revenue guidance reaffirmed at "
                "$2.10 to $2.25 billion."
            ),
            start_char=8,
            value=(
                "Full-year 2026 revenue guidance reaffirmed at "
                "$2.10 to $2.25 billion."
            ),
        )
        llm_client = LLMClient(
            make_llm_config(),
            anthropic_client=QueuedAnthropicClient([{"candidates": (payload,)}]),
        )

        result = await execute_plan(
            plan=make_plan(max_calls=1),
            chunks=(chunk,),
            prompt_loader=PromptLoader(ROOT / "prompts"),
            llm_client=llm_client,
            execution_config=make_execution_config(),
        )

        assert len(result.accepted_candidates) == 1
        assert result.rejected_candidates == ()
        assert result.accepted_candidates[0].source_span.start_char == 0
        assert result.accepted_candidates[0].source_span.text == chunk_text

    asyncio.run(run_check())


def test_execute_plan_rejects_malformed_payload_offsets_without_aborting(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        # Model claims a source_length that does not fit the chunk; this should
        # be logged as a rejection instead of aborting.
        malformed_payload = candidate_payload(
            start_char=0,
            value="Missing source value",
            source_length=999,
        )
        llm_client = LLMClient(
            make_llm_config(),
            anthropic_client=QueuedAnthropicClient([{"candidates": (malformed_payload,)}]),
        )

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store)
            result = await execute_plan(
                plan=make_plan(max_calls=1),
                chunks=(make_chunks()[0],),
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                execution_config=make_execution_config(),
                audit_store=audit_store,
            )
            stored_candidates = await audit_store.list_lens_candidates("run-1")

        assert result.accepted_candidates == ()
        assert len(result.rejected_candidates) == 1
        assert len(stored_candidates) == 1
        assert result.rejections[0].reasons[0].code == "invalid_source_offsets"

    asyncio.run(run_check())


def test_execute_plan_accepts_start_text_typo_as_start_char(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        payload = candidate_payload()
        payload["start_text"] = payload.pop("start_char")
        llm_client = LLMClient(
            make_llm_config(),
            anthropic_client=QueuedAnthropicClient([{"candidates": (payload,)}]),
        )

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store)
            result = await execute_plan(
                plan=make_plan(max_calls=1),
                chunks=(make_chunks()[0],),
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                execution_config=make_execution_config(),
                audit_store=audit_store,
            )

        assert len(result.accepted_candidates) == 1
        assert result.accepted_candidates[0].source_span.start_char == 0
        assert result.rejected_candidates == ()

    asyncio.run(run_check())


def test_execute_plan_rejects_insufficient_lens_budget_before_llm_calls() -> None:
    async def run_check() -> None:
        anthropic_client = QueuedAnthropicClient([])
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        with pytest.raises(ExecutorError, match="budget"):
            await execute_plan(
                plan=make_plan(max_calls=1),
                chunks=make_chunks(),
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                execution_config=make_execution_config(),
            )

        assert anthropic_client.messages.calls == []

    asyncio.run(run_check())


def test_execute_plan_rejects_chunk_document_mismatch() -> None:
    async def run_check() -> None:
        bad_chunk = make_chunks()[0].model_copy(update={"doc_id": "doc-2"})
        llm_client = LLMClient(make_llm_config(), anthropic_client=QueuedAnthropicClient([]))

        with pytest.raises(ExecutorError, match="chunk doc_id must match"):
            await execute_plan(
                plan=make_plan(max_calls=1),
                chunks=(bad_chunk,),
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                execution_config=make_execution_config(),
            )

    asyncio.run(run_check())
