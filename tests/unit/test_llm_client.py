import asyncio
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import BaseModel, ConfigDict, Field

from extractor.audit import AuditStore
from extractor.config import LLMConfig
from extractor.contracts import RunManifest
from extractor.llm import (
    Accepted,
    Complaints,
    ItemComplaint,
    LLMClient,
    LLMClientError,
    LLMRetryMergeError,
    LLMToolUseError,
    PROMPT_STAGES,
    PromptLoadError,
    PromptLoader,
    PromptTemplate,
    StructuredLLMRequest,
)


ROOT = Path(__file__).resolve().parents[2]


PROMPT_TEXT = """\
# executor.claim

## Intent
Extract claim candidates from one chunk.

## Typed Inputs
Chunk text plus approved categories.

## Output Tool Schema
Use the extract_claim tool input schema.

## Failure Modes
Return no candidates when evidence is insufficient.

## Prompt
Read the chunk and call the tool.
"""


class ExtractClaimOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    value: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class OptionalDetail(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(min_length=1)
    score: float | None = None


class OptionalClaimOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    value: str = Field(min_length=1)
    detail: OptionalDetail | None = None


class FakeMessages:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return self.response


class FakeAnthropicClient:
    def __init__(self, response: object) -> None:
        self.messages = FakeMessages(response)


class FakeOpenAICompletions:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return self.response


class FakeOpenAIClient:
    def __init__(self, response: object) -> None:
        self.chat = SimpleNamespace(completions=FakeOpenAICompletions(response))


def make_prompt_template() -> PromptTemplate:
    return PromptTemplate(
        stage="executor.claim",
        path=Path("prompts/executor/claim.md"),
        text=PROMPT_TEXT,
        intent="Extract claim candidates from one chunk.",
        typed_inputs="Chunk text plus approved categories.",
        output_tool_schema="Use the extract_claim tool input schema.",
        failure_modes="Return no candidates when evidence is insufficient.",
        body="Read the chunk and call the tool.",
    )


def make_request() -> StructuredLLMRequest:
    return StructuredLLMRequest(
        run_id="run-1",
        stage="executor.claim",
        prompt=make_prompt_template(),
        user_content="hello world",
        tool_name="extract_claim",
        tool_description="Return extracted claim candidates.",
    )


def make_response(content: list[object]) -> SimpleNamespace:
    return SimpleNamespace(
        content=content,
        stop_reason="tool_use",
        usage=SimpleNamespace(
            input_tokens=12,
            output_tokens=7,
            cache_read_input_tokens=3,
            cache_creation_input_tokens=2,
        ),
    )


def make_openai_response(
    tool_calls: list[object] | None,
    *,
    finish_reason: str = "tool_calls",
) -> SimpleNamespace:
    return SimpleNamespace(
        choices=(
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(tool_calls=tool_calls),
            ),
        ),
        usage=SimpleNamespace(
            prompt_tokens=14,
            completion_tokens=8,
            prompt_tokens_details=SimpleNamespace(cached_tokens=4),
        ),
    )


def make_config(
    *,
    prompt_cache_enabled: bool = True,
    min_request_interval_seconds: int = 0,
) -> LLMConfig:
    return LLMConfig(
        provider="anthropic",
        model="configured-model",
        max_retries=0,
        min_request_interval_seconds=min_request_interval_seconds,
        timeout_seconds=30,
        max_output_tokens=512,
        temperature=0.0,
        prompt_cache_enabled=prompt_cache_enabled,
    )


def make_openai_config() -> LLMConfig:
    return LLMConfig(
        provider="openai",
        model="gpt-5.2",
        max_retries=0,
        timeout_seconds=30,
        max_output_tokens=512,
        temperature=0.0,
    )


def make_openai_config_with_stage_override() -> LLMConfig:
    return LLMConfig(
        provider="openai",
        model="gpt-5-mini",
        max_retries=0,
        timeout_seconds=30,
        max_output_tokens=512,
        temperature=0.0,
        stage_overrides={
            "executor": {
                "model": "gpt-5.2",
                "max_output_tokens": 1024,
                "reasoning_effort": "high",
            }
        },
    )


def make_openai_compatible_config() -> LLMConfig:
    return LLMConfig(
        provider="openai_compatible",
        base_url="https://api.moonshot.ai/v1",
        api_key_env="MOONSHOT_API_KEY",
        model="kimi-k2.6",
        max_retries=0,
        timeout_seconds=30,
        max_output_tokens=512,
        temperature=0.0,
    )


def make_manifest() -> RunManifest:
    return RunManifest(
        run_id="run-1",
        doc_id="doc-1",
        audit_db_path="/tmp/audit.sqlite3",
        status="created",
        started_at=datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc),
        output_data_point_ids=(),
    )


def test_prompt_loader_reads_documented_prompt_sections(tmp_path: Path) -> None:
    prompt_path = tmp_path / "executor" / "claim.md"
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text(PROMPT_TEXT, encoding="utf-8")

    prompt = PromptLoader(tmp_path).load("executor.claim")

    assert prompt.stage == "executor.claim"
    assert prompt.path == prompt_path
    assert prompt.body == "Read the chunk and call the tool."
    assert prompt.sha256 == hashlib.sha256(PROMPT_TEXT.encode("utf-8")).hexdigest()


def test_prompt_loader_rejects_missing_required_sections(tmp_path: Path) -> None:
    prompt_path = tmp_path / "executor" / "claim.md"
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text("# executor.claim\n\n## Intent\nExtract claims.\n", encoding="utf-8")

    with pytest.raises(PromptLoadError, match="missing required section"):
        PromptLoader(tmp_path).load("executor.claim")


def test_default_prompt_pack_loads_for_all_stages() -> None:
    prompts = PromptLoader(ROOT / "prompts").load_all()

    assert tuple(prompt.stage for prompt in prompts) == PROMPT_STAGES
    assert all("prompt-placeholder" not in prompt.body for prompt in prompts)
    assert all("Call the required tool exactly once" in prompt.body for prompt in prompts)


def test_default_prompt_pack_contains_source_provenance_rules() -> None:
    prompts = {prompt.stage: prompt for prompt in PromptLoader(ROOT / "prompts").load_all()}

    for stage in ("executor.entity", "executor.event", "executor.claim", "executor.number"):
        body = prompts[stage].body
        assert "absolute document character offsets" in body or "absolute document character offset" in body
        assert "start_char = chunk_view.start_char + chunk_relative_index" in body
        assert "Do not estimate start_char" in body
        # Source text and bytes are now derived server-side; the prompts must
        # NOT ask the model to produce them, since LLM copying/byte arithmetic
        # is expensive and unreliable.
        assert "byte offsets are derived server-side" in body
        assert "Return source_length as the number of characters" in body
        assert (
            "chunk_view.text[start_char - chunk_view.start_char : start_char - chunk_view.start_char + "
            "source_length]"
        ) in body
        assert "Never output source_text" in body
        assert "start_text" in body
        assert "end_char, start_byte, or end_byte" in body

    assert "Every input candidate must be accounted for exactly once" in prompts["reconciler"].body
    assert 'decision_code="a" only when' in prompts["verifier"].body


def test_default_prompt_pack_contains_hardening_examples_and_checklists() -> None:
    prompts = {prompt.stage: prompt for prompt in PromptLoader(ROOT / "prompts").load_all()}

    for stage in ("executor.entity", "executor.event", "executor.claim", "executor.number"):
        body = prompts[stage].body
        assert "Few-shot examples:" in body
        assert "Reject:" in body
        assert "Preflight checklist" in body

    assert "Anti-patterns:" in prompts["planner.classify_document"].body
    assert "The summary must be one or two concise sentences" in prompts["planner.classify_document"].body
    assert "Schema anti-patterns:" in prompts["planner.propose_schema"].body
    assert "Avoid synonym drift" in prompts["planner.propose_schema"].body
    assert "Adversarial checklist:" in prompts["planner.critique_schema"].body
    assert "Reject synonym drift" in prompts["planner.critique_schema"].body
    assert "Selection examples:" in prompts["planner.select_strategy"].body
    assert "The rationale must explain lens coverage" in prompts["planner.select_strategy"].body
    assert "Budget examples:" in prompts["planner.allocate_budget"].body
    assert "Adversarial checklist:" in prompts["critic"].body
    assert "Adversarial checklist:" in prompts["verifier"].body
    assert "Reconciliation examples:" in prompts["reconciler"].body
    assert "Final audit checklist:" in prompts["reconciler"].body


def test_llm_client_forces_tool_use_and_records_audit_log(tmp_path: Path) -> None:
    async def run_check() -> None:
        response = make_response(
            [
                SimpleNamespace(
                    type="tool_use",
                    name="extract_claim",
                    input={"value": "hello world", "confidence": 0.9},
                )
            ]
        )
        anthropic_client = FakeAnthropicClient(response)
        client = LLMClient(
            make_config(prompt_cache_enabled=False),
            anthropic_client=anthropic_client,
        )

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await audit_store.record_run_manifest(make_manifest())
            result = await client.complete_structured(
                make_request(),
                output_model=ExtractClaimOutput,
                audit_store=audit_store,
            )
            logs = await audit_store.list_llm_call_logs("run-1")

        assert result.output == ExtractClaimOutput(value="hello world", confidence=0.9)
        assert result.call_log == logs[0]
        assert logs[0].stage == "executor.claim"
        assert logs[0].model == "configured-model"
        assert logs[0].prompt_sha256 == hashlib.sha256(PROMPT_TEXT.encode("utf-8")).hexdigest()
        assert logs[0].input_tokens == 12
        assert logs[0].output_tokens == 7
        assert logs[0].cache_read_tokens == 3
        assert logs[0].cache_creation_tokens == 2
        assert logs[0].tool_name == "extract_claim"

        call = anthropic_client.messages.calls[0]
        assert call["model"] == "configured-model"
        assert call["max_tokens"] == 512
        assert call["temperature"] == 0.0
        assert call["system"] == PROMPT_TEXT
        assert call["messages"] == [{"role": "user", "content": "hello world"}]
        assert call["tool_choice"] == {"type": "tool", "name": "extract_claim"}
        assert call["tools"][0]["name"] == "extract_claim"
        assert call["tools"][0]["input_schema"]["properties"]["value"]["type"] == "string"

    asyncio.run(run_check())


def test_llm_client_throttles_request_starts() -> None:
    async def run_check() -> None:
        now = 100.0
        sleep_calls: list[float] = []

        def monotonic() -> float:
            return now

        async def fake_sleep(delay: float) -> None:
            nonlocal now
            sleep_calls.append(delay)
            now += delay

        response = make_response(
            [
                SimpleNamespace(
                    type="tool_use",
                    name="extract_claim",
                    input={"value": "hello world", "confidence": 0.9},
                )
            ]
        )
        anthropic_client = FakeAnthropicClient(response)
        client = LLMClient(
            make_config(
                prompt_cache_enabled=False,
                min_request_interval_seconds=60,
            ),
            anthropic_client=anthropic_client,
            monotonic=monotonic,
            sleep=fake_sleep,
        )

        await client.complete_structured(
            make_request(),
            output_model=ExtractClaimOutput,
        )
        await client.complete_structured(
            make_request(),
            output_model=ExtractClaimOutput,
        )

        assert sleep_calls == [60.0]
        assert len(anthropic_client.messages.calls) == 2

    asyncio.run(run_check())


def test_llm_client_sends_anthropic_prompt_cache_blocks() -> None:
    async def run_check() -> None:
        response = make_response(
            [
                SimpleNamespace(
                    type="tool_use",
                    name="extract_claim",
                    input={"value": "hello world", "confidence": 0.9},
                )
            ]
        )
        anthropic_client = FakeAnthropicClient(response)
        request = make_request().model_copy(
            update={
                "stage": "critic",
                "stable_user_prefix": '{"run_id":"run-1","candidates":',
                "user_content": "[]}",
            },
        )
        client = LLMClient(make_config(), anthropic_client=anthropic_client)

        result = await client.complete_structured(
            request,
            output_model=ExtractClaimOutput,
        )

        assert result.output == ExtractClaimOutput(value="hello world", confidence=0.9)
        call = anthropic_client.messages.calls[0]
        assert call["system"] == [
            {
                "type": "text",
                "text": PROMPT_TEXT,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        assert call["tools"][0]["cache_control"] == {"type": "ephemeral"}
        assert call["messages"] == [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": '{"run_id":"run-1","candidates":',
                        "cache_control": {"type": "ephemeral"},
                    },
                    {"type": "text", "text": "[]}"},
                ],
            }
        ]

    asyncio.run(run_check())


def test_llm_client_honors_anthropic_prompt_cache_opt_out() -> None:
    async def run_check() -> None:
        response = make_response(
            [
                SimpleNamespace(
                    type="tool_use",
                    name="extract_claim",
                    input={"value": "hello world", "confidence": 0.9},
                )
            ]
        )
        anthropic_client = FakeAnthropicClient(response)
        request = make_request().model_copy(
            update={
                "stage": "critic",
                "stable_user_prefix": '{"run_id":"run-1","candidates":',
                "user_content": "[]}",
                "prompt_cache_allowed": False,
            },
        )
        client = LLMClient(make_config(), anthropic_client=anthropic_client)

        await client.complete_structured(request, output_model=ExtractClaimOutput)

        call = anthropic_client.messages.calls[0]
        assert call["system"] == PROMPT_TEXT
        assert call["messages"] == [
            {
                "role": "user",
                "content": '{"run_id":"run-1","candidates":[]}',
            }
        ]
        assert "cache_control" not in call["tools"][0]

    asyncio.run(run_check())


def test_llm_client_preserves_anthropic_payload_shape_when_prompt_cache_disabled() -> None:
    async def run_check() -> None:
        response = make_response(
            [
                SimpleNamespace(
                    type="tool_use",
                    name="extract_claim",
                    input={"value": "hello world", "confidence": 0.9},
                )
            ]
        )
        anthropic_client = FakeAnthropicClient(response)
        request = make_request().model_copy(
            update={
                "stable_user_prefix": '{"run_id":"run-1","candidates":',
                "user_content": "[]}",
            },
        )
        client = LLMClient(
            make_config(prompt_cache_enabled=False),
            anthropic_client=anthropic_client,
        )

        await client.complete_structured(request, output_model=ExtractClaimOutput)

        call = anthropic_client.messages.calls[0]
        assert call["system"] == PROMPT_TEXT
        assert call["messages"] == [
            {
                "role": "user",
                "content": '{"run_id":"run-1","candidates":[]}',
            }
        ]
        assert "cache_control" not in call["tools"][0]

    asyncio.run(run_check())


def test_llm_client_supports_openai_forced_tool_calls_and_audit_log(tmp_path: Path) -> None:
    async def run_check() -> None:
        response = make_openai_response(
            [
                SimpleNamespace(
                    type="function",
                    function=SimpleNamespace(
                        name="extract_claim",
                        arguments='{"value": "hello world", "confidence": 0.9}',
                    ),
                )
            ]
        )
        openai_client = FakeOpenAIClient(response)
        client = LLMClient(make_openai_config(), openai_client=openai_client)

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await audit_store.record_run_manifest(make_manifest())
            result = await client.complete_structured(
                make_request(),
                output_model=ExtractClaimOutput,
                audit_store=audit_store,
            )
            logs = await audit_store.list_llm_call_logs("run-1")

        assert result.output == ExtractClaimOutput(value="hello world", confidence=0.9)
        assert result.call_log == logs[0]
        assert logs[0].stage == "executor.claim"
        assert logs[0].model == "gpt-5.2"
        assert logs[0].input_tokens == 14
        assert logs[0].output_tokens == 8
        assert logs[0].cache_read_tokens == 4
        assert logs[0].cache_creation_tokens == 0
        assert logs[0].stop_reason == "tool_calls"
        assert logs[0].tool_name == "extract_claim"

        call = openai_client.chat.completions.calls[0]
        assert call["model"] == "gpt-5.2"
        assert call["max_completion_tokens"] == 512
        # gpt-5* reasoning models reject any non-default temperature and accept reasoning_effort.
        assert "temperature" not in call
        assert call["reasoning_effort"] == "medium"
        assert call["messages"] == [
            {"role": "system", "content": PROMPT_TEXT},
            {"role": "user", "content": "hello world"},
        ]
        assert call["tool_choice"] == {
            "type": "function",
            "function": {"name": "extract_claim"},
        }
        assert call["parallel_tool_calls"] is False
        assert call["tools"][0]["type"] == "function"
        assert call["tools"][0]["function"]["name"] == "extract_claim"
        assert call["tools"][0]["function"]["strict"] is True
        assert call["tools"][0]["function"]["parameters"]["properties"]["value"][
            "type"
        ] == "string"

    asyncio.run(run_check())


def test_llm_client_supports_kimi_forced_tool_calls_with_thinking_disabled(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        response = make_openai_response(
            [
                SimpleNamespace(
                    type="function",
                    function=SimpleNamespace(
                        name="extract_claim",
                        arguments='{"value": "hello world", "confidence": 0.9}',
                    ),
                )
            ]
        )
        openai_client = FakeOpenAIClient(response)
        client = LLMClient(
            make_openai_compatible_config(),
            openai_client=openai_client,
        )

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await audit_store.record_run_manifest(make_manifest())
            result = await client.complete_structured(
                make_request(),
                output_model=ExtractClaimOutput,
                audit_store=audit_store,
            )
            logs = await audit_store.list_llm_call_logs("run-1")

        assert result.output == ExtractClaimOutput(value="hello world", confidence=0.9)
        assert logs[0].model == "kimi-k2.6"

        call = openai_client.chat.completions.calls[0]
        assert call["model"] == "kimi-k2.6"
        assert call["max_tokens"] == 512
        assert "max_completion_tokens" not in call
        assert call["tool_choice"] == {
            "type": "function",
            "function": {"name": "extract_claim"},
        }
        assert call["extra_body"] == {"thinking": {"type": "disabled"}}
        assert call["parallel_tool_calls"] is False
        assert "temperature" not in call
        assert "reasoning_effort" not in call

    asyncio.run(run_check())


def test_llm_client_rejects_missing_openai_compatible_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)

    with pytest.raises(LLMClientError, match="MOONSHOT_API_KEY"):
        LLMClient(make_openai_compatible_config())


def test_llm_client_applies_openai_stage_model_overrides_and_audit_log(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        response = make_openai_response(
            [
                SimpleNamespace(
                    type="function",
                    function=SimpleNamespace(
                        name="extract_claim",
                        arguments='{"value": "hello world", "confidence": 0.9}',
                    ),
                )
            ]
        )
        openai_client = FakeOpenAIClient(response)
        client = LLMClient(
            make_openai_config_with_stage_override(),
            openai_client=openai_client,
        )

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await audit_store.record_run_manifest(make_manifest())
            result = await client.complete_structured(
                make_request(),
                output_model=ExtractClaimOutput,
                audit_store=audit_store,
            )
            logs = await audit_store.list_llm_call_logs("run-1")

        assert result.call_log == logs[0]
        assert logs[0].stage == "executor.claim"
        assert logs[0].model == "gpt-5.2"

        call = openai_client.chat.completions.calls[0]
        assert call["model"] == "gpt-5.2"
        assert call["max_completion_tokens"] == 1024
        assert call["reasoning_effort"] == "high"

    asyncio.run(run_check())


def test_llm_client_sends_openai_strict_schema_for_optional_fields() -> None:
    async def run_check() -> None:
        response = make_openai_response(
            [
                SimpleNamespace(
                    type="function",
                    function=SimpleNamespace(
                        name="extract_claim",
                        arguments='{"value": "hello world", "detail": null}',
                    ),
                )
            ]
        )
        openai_client = FakeOpenAIClient(response)
        client = LLMClient(make_openai_config(), openai_client=openai_client)

        result = await client.complete_structured(
            make_request(),
            output_model=OptionalClaimOutput,
        )

        assert result.output == OptionalClaimOutput(value="hello world", detail=None)
        parameters = openai_client.chat.completions.calls[0]["tools"][0]["function"][
            "parameters"
        ]
        assert parameters["required"] == ["value", "detail"]
        assert "default" not in parameters["properties"]["detail"]
        assert parameters["$defs"]["OptionalDetail"]["required"] == ["text", "score"]
        assert "default" not in parameters["$defs"]["OptionalDetail"]["properties"]["score"]

    asyncio.run(run_check())


def test_llm_client_rejects_free_text_responses_without_parsing_json() -> None:
    async def run_check() -> None:
        response = make_response([SimpleNamespace(type="text", text='{"value": "not accepted"}')])
        client = LLMClient(make_config(), anthropic_client=FakeAnthropicClient(response))

        with pytest.raises(LLMToolUseError, match="required tool_use"):
            await client.complete_structured(make_request(), output_model=ExtractClaimOutput)

    asyncio.run(run_check())


def test_llm_client_rejects_openai_responses_without_required_tool_call() -> None:
    async def run_check() -> None:
        response = make_openai_response(None, finish_reason="stop")
        client = LLMClient(make_openai_config(), openai_client=FakeOpenAIClient(response))

        with pytest.raises(LLMToolUseError, match="required tool call"):
            await client.complete_structured(make_request(), output_model=ExtractClaimOutput)

    asyncio.run(run_check())


def test_llm_client_rejects_openai_wrong_tool_name() -> None:
    async def run_check() -> None:
        response = make_openai_response(
            [
                SimpleNamespace(
                    type="function",
                    function=SimpleNamespace(
                        name="wrong_tool",
                        arguments='{"value": "hello world", "confidence": 0.9}',
                    ),
                )
            ]
        )
        client = LLMClient(make_openai_config(), openai_client=FakeOpenAIClient(response))

        with pytest.raises(LLMToolUseError, match="Expected OpenAI tool call named extract_claim"):
            await client.complete_structured(make_request(), output_model=ExtractClaimOutput)

    asyncio.run(run_check())


def test_llm_client_rejects_openai_malformed_tool_arguments() -> None:
    async def run_check() -> None:
        response = make_openai_response(
            [
                SimpleNamespace(
                    type="function",
                    function=SimpleNamespace(
                        name="extract_claim",
                        arguments='{"value": "hello world"',
                    ),
                )
            ]
        )
        client = LLMClient(make_openai_config(), openai_client=FakeOpenAIClient(response))

        with pytest.raises(LLMToolUseError, match="valid JSON"):
            await client.complete_structured(make_request(), output_model=ExtractClaimOutput)

    asyncio.run(run_check())


class QueuedAnthropicMessages:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("unexpected extra Anthropic call")
        return self.responses.pop(0)


class QueuedAnthropicClient:
    def __init__(self, responses: list[object]) -> None:
        self.messages = QueuedAnthropicMessages(responses)


def make_tool_response(
    *,
    tool_name: str,
    tool_input: dict[str, object],
    block_id: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        content=[
            SimpleNamespace(
                type="tool_use",
                id=block_id,
                name=tool_name,
                input=tool_input,
            )
        ],
        stop_reason="tool_use",
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=5,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        ),
    )


def test_complete_structured_with_retry_returns_first_when_validator_accepts(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        response = make_tool_response(
            tool_name="extract_claim",
            tool_input={"value": "hello", "confidence": 0.9},
            block_id="toolu_a1",
        )
        anthropic_client = QueuedAnthropicClient([response])
        client = LLMClient(
            make_config(prompt_cache_enabled=False),
            anthropic_client=anthropic_client,
        )

        def validator(_: ExtractClaimOutput) -> Accepted[ExtractClaimOutput] | Complaints:
            return Accepted(output=_)

        def merger(*_: object) -> ExtractClaimOutput:
            raise AssertionError("merger should not be invoked")

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await audit_store.record_run_manifest(make_manifest())
            result = await client.complete_structured_with_retry(
                make_request(),
                output_model=ExtractClaimOutput,
                audit_store=audit_store,
                validate=validator,
                merge=merger,
                max_retries=1,
            )
            logs = await audit_store.list_llm_call_logs("run-1")

        assert len(anthropic_client.messages.calls) == 1
        assert [log.attempt for log in logs] == [1]
        assert result.output == ExtractClaimOutput(value="hello", confidence=0.9)
        assert result.call_log == logs[0]

    asyncio.run(run_check())


def test_complete_structured_with_retry_sends_tool_result_complaint_and_merges(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        first = make_tool_response(
            tool_name="extract_claim",
            tool_input={"value": "wrong", "confidence": 0.9},
            block_id="toolu_first",
        )
        second = make_tool_response(
            tool_name="extract_claim",
            tool_input={"value": "fixed", "confidence": 0.95},
            block_id="toolu_second",
        )
        anthropic_client = QueuedAnthropicClient([first, second])
        client = LLMClient(
            make_config(prompt_cache_enabled=False),
            anthropic_client=anthropic_client,
        )

        def validator(
            output: ExtractClaimOutput,
        ) -> Accepted[ExtractClaimOutput] | Complaints:
            if output.value == "wrong":
                return Complaints(
                    complaints=(
                        ItemComplaint(
                            identifier="0",
                            message="value 'wrong' must be 'fixed'.",
                        ),
                    )
                )
            return Accepted(output=output)

        merge_calls: list[frozenset[str]] = []

        def merger(
            prior: ExtractClaimOutput,
            retry: ExtractClaimOutput,
            ids: frozenset[str],
        ) -> ExtractClaimOutput:
            merge_calls.append(ids)
            return retry

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await audit_store.record_run_manifest(make_manifest())
            result = await client.complete_structured_with_retry(
                make_request(),
                output_model=ExtractClaimOutput,
                audit_store=audit_store,
                validate=validator,
                merge=merger,
                max_retries=1,
            )
            logs = await audit_store.list_llm_call_logs("run-1")

        assert len(anthropic_client.messages.calls) == 2
        assert [log.attempt for log in logs] == [1, 2]
        assert result.output == ExtractClaimOutput(value="fixed", confidence=0.95)
        assert merge_calls == [frozenset({"0"})]

        retry_messages = anthropic_client.messages.calls[1]["messages"]
        assert len(retry_messages) == 3
        assert retry_messages[0]["role"] == "user"
        assert retry_messages[1]["role"] == "assistant"
        assistant_blocks = retry_messages[1]["content"]
        assert assistant_blocks[0]["type"] == "tool_use"
        assert assistant_blocks[0]["id"] == "toolu_first"
        assert assistant_blocks[0]["name"] == "extract_claim"
        assert assistant_blocks[0]["input"] == {"value": "wrong", "confidence": 0.9}
        assert retry_messages[2]["role"] == "user"
        tool_result = retry_messages[2]["content"][0]
        assert tool_result["type"] == "tool_result"
        assert tool_result["tool_use_id"] == "toolu_first"
        assert tool_result["is_error"] is True
        assert "value 'wrong' must be 'fixed'." in tool_result["content"]

    asyncio.run(run_check())


def test_complete_structured_with_retry_returns_prior_when_merge_raises(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        first = make_tool_response(
            tool_name="extract_claim",
            tool_input={"value": "wrong", "confidence": 0.9},
            block_id="toolu_first",
        )
        second = make_tool_response(
            tool_name="extract_claim",
            tool_input={"value": "still wrong", "confidence": 0.9},
            block_id="toolu_second",
        )
        anthropic_client = QueuedAnthropicClient([first, second])
        client = LLMClient(
            make_config(prompt_cache_enabled=False),
            anthropic_client=anthropic_client,
        )

        def validator(
            output: ExtractClaimOutput,
        ) -> Accepted[ExtractClaimOutput] | Complaints:
            return Complaints(
                complaints=(ItemComplaint(identifier="0", message="bad"),)
            )

        def merger(*_: object) -> ExtractClaimOutput:
            raise LLMRetryMergeError("count mismatch")

        result = await client.complete_structured_with_retry(
            make_request(),
            output_model=ExtractClaimOutput,
            validate=validator,
            merge=merger,
            max_retries=1,
        )

        assert len(anthropic_client.messages.calls) == 2
        assert result.output == ExtractClaimOutput(value="wrong", confidence=0.9)

    asyncio.run(run_check())


def test_complete_structured_with_retry_skips_retry_when_max_is_zero() -> None:
    async def run_check() -> None:
        first = make_tool_response(
            tool_name="extract_claim",
            tool_input={"value": "wrong", "confidence": 0.9},
            block_id="toolu_first",
        )
        anthropic_client = QueuedAnthropicClient([first])
        client = LLMClient(
            make_config(prompt_cache_enabled=False),
            anthropic_client=anthropic_client,
        )

        def validator(
            output: ExtractClaimOutput,
        ) -> Accepted[ExtractClaimOutput] | Complaints:
            return Complaints(
                complaints=(ItemComplaint(identifier="0", message="bad"),)
            )

        result = await client.complete_structured_with_retry(
            make_request(),
            output_model=ExtractClaimOutput,
            validate=validator,
            merge=lambda p, r, i: r,
            max_retries=0,
        )

        assert len(anthropic_client.messages.calls) == 1
        assert result.output == ExtractClaimOutput(value="wrong", confidence=0.9)

    asyncio.run(run_check())


def test_complete_structured_with_retry_rejects_openai_provider() -> None:
    async def run_check() -> None:
        client = LLMClient(
            make_openai_config(),
            openai_client=FakeOpenAIClient(SimpleNamespace()),
        )
        with pytest.raises(NotImplementedError):
            await client.complete_structured_with_retry(
                make_request(),
                output_model=ExtractClaimOutput,
                validate=lambda o: Accepted(output=o),
                merge=lambda p, r, i: r,
                max_retries=1,
            )

    asyncio.run(run_check())


def test_llm_client_rejects_unexpected_tool_name() -> None:
    async def run_check() -> None:
        response = make_response(
            [
                SimpleNamespace(
                    type="tool_use",
                    name="wrong_tool",
                    input={"value": "hello world", "confidence": 0.9},
                )
            ]
        )
        client = LLMClient(make_config(), anthropic_client=FakeAnthropicClient(response))

        with pytest.raises(LLMToolUseError, match="Expected tool_use named extract_claim"):
            await client.complete_structured(make_request(), output_model=ExtractClaimOutput)

    asyncio.run(run_check())
