from __future__ import annotations

import json
import os
import sys
import time
import uuid

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from extractor.audit import AuditStore
from extractor.config import LLMConfig
from extractor.contracts import LLMCallLog
from extractor.contracts.models import LLMStage
from extractor.llm.prompts import PromptTemplate


_OPENAI_COMPATIBLE_PROVIDERS = {"openai", "openai_compatible"}
_ANTHROPIC_CACHEABLE_STAGE_GROUPS = {"planner", "executor", "critic", "verifier"}
_ANTHROPIC_EPHEMERAL_CACHE_CONTROL = {"type": "ephemeral"}
# Visual divider widths for the human-readable LLM trace lines.
_TRACE_OUTER = "=" * 100
_TRACE_INNER = "-" * 100
# Per-section character cap so giant prompts/payloads stay readable in a terminal.
_TRACE_MAX_SECTION_CHARS = 4000


def _trace_enabled() -> bool:
    # Default the trace to ON. Set EXTRACTOR_LLM_TRACE=0 to silence it.
    # Name avoids the VERITEXT_ prefix so the config loader doesn't try to bind it.
    return os.environ.get("EXTRACTOR_LLM_TRACE", "1") not in {"0", "false", "False", ""}


def _truncate_for_trace(text: str) -> str:
    if len(text) <= _TRACE_MAX_SECTION_CHARS:
        return text
    head = text[:_TRACE_MAX_SECTION_CHARS]
    return f"{head}\n... [truncated {len(text) - _TRACE_MAX_SECTION_CHARS} chars] ..."


def _stage_group(stage: LLMStage) -> str:
    return stage.split(".", 1)[0]


def _print_llm_trace(
    *,
    request: "StructuredLLMRequest",
    output: BaseModel,
    call_log: LLMCallLog,
) -> None:
    if not _trace_enabled():
        return
    group = _stage_group(request.stage)
    header = f" -> {group.upper():<10} | stage={request.stage}  call_id={call_log.call_id}"
    try:
        rendered_output = output.model_dump_json(indent=2)
    except Exception:
        rendered_output = repr(output)
    parts = [
        "",
        _TRACE_OUTER,
        header,
        _TRACE_OUTER,
        "[SYSTEM PROMPT]",
        _truncate_for_trace(request.prompt.text),
        _TRACE_INNER,
        "[USER]",
        _truncate_for_trace(request.full_user_content),
        _TRACE_INNER,
        "[RESPONSE / TOOL INPUT]",
        _truncate_for_trace(rendered_output),
        _TRACE_INNER,
        (
            f"[USAGE] model={call_log.model} "
            f"in={call_log.input_tokens} out={call_log.output_tokens} "
            f"cache_read={call_log.cache_read_tokens} "
            f"latency_ms={call_log.latency_ms} "
            f"stop_reason={call_log.stop_reason} "
            f"tool={call_log.tool_name}"
        ),
        _TRACE_OUTER,
        "",
    ]
    print("\n".join(parts), file=sys.stderr, flush=True)


OutputModelT = TypeVar("OutputModelT", bound=BaseModel)
NonEmptyStr = Annotated[str, Field(strict=True, min_length=1)]


class LLMClientError(RuntimeError):
    """Base class for LLM client failures."""


class LLMToolUseError(LLMClientError):
    """Raised when the model response does not contain the required tool call."""


class LLMRetryMergeError(LLMClientError):
    """Raised when a retry response cannot be reconciled with the prior batch."""


@dataclass(frozen=True)
class ItemComplaint:
    identifier: str
    message: str


@dataclass(frozen=True)
class Accepted(Generic[OutputModelT]):
    output: OutputModelT


@dataclass(frozen=True)
class Complaints:
    complaints: tuple[ItemComplaint, ...]


class StructuredLLMRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(strict=True, min_length=1)
    stage: LLMStage
    prompt: PromptTemplate
    user_content: str = Field(strict=True)
    stable_user_prefix: NonEmptyStr | None = None
    prompt_cache_allowed: bool = Field(default=True, strict=True)
    tool_name: str = Field(strict=True, min_length=1)
    tool_description: str = Field(strict=True, min_length=1)

    @model_validator(mode="after")
    def validate_user_content(self) -> StructuredLLMRequest:
        if not self.user_content and self.stable_user_prefix is None:
            raise ValueError("user_content must be non-empty unless stable_user_prefix is set")
        return self

    @property
    def full_user_content(self) -> str:
        return f"{self.stable_user_prefix or ''}{self.user_content}"


class StructuredLLMResult(BaseModel, Generic[OutputModelT]):
    model_config = ConfigDict(extra="forbid", frozen=True)

    output: OutputModelT
    call_log: LLMCallLog


@dataclass(frozen=True)
class _ResolvedLLMSettings:
    model: str
    max_output_tokens: int
    reasoning_effort: str


@dataclass(frozen=True)
class _OpenAIModelFamily:
    is_reasoning: bool
    is_kimi: bool


class LLMClient:
    def __init__(
        self,
        config: LLMConfig,
        *,
        anthropic_client: object | None = None,
        openai_client: object | None = None,
    ) -> None:
        self.config = config
        self._anthropic_client = (
            anthropic_client if config.provider == "anthropic" else None
        )
        self._openai_client = (
            openai_client if _uses_openai_chat_client(config) else None
        )
        if config.provider == "anthropic" and self._anthropic_client is None:
            self._anthropic_client = _create_anthropic_client(config)
        if _uses_openai_chat_client(config) and self._openai_client is None:
            self._openai_client = _create_openai_client(config)

    async def complete_structured(
        self,
        request: StructuredLLMRequest,
        *,
        output_model: type[OutputModelT],
        audit_store: AuditStore | None = None,
    ) -> StructuredLLMResult[OutputModelT]:
        if self.config.provider == "anthropic":
            return await self._complete_anthropic(
                request,
                output_model=output_model,
                audit_store=audit_store,
            )
        if _uses_openai_chat_client(self.config):
            return await self._complete_openai(
                request,
                output_model=output_model,
                audit_store=audit_store,
            )
        raise LLMClientError(f"Unsupported LLM provider: {self.config.provider}")

    async def _complete_anthropic(
        self,
        request: StructuredLLMRequest,
        *,
        output_model: type[OutputModelT],
        audit_store: AuditStore | None = None,
    ) -> StructuredLLMResult[OutputModelT]:
        settings = _resolve_llm_settings(self.config, request.stage)
        cache_enabled = _anthropic_prompt_cache_enabled(self.config, request)
        initial_user_content = _anthropic_user_content(request, cache_enabled=cache_enabled)
        messages: list[dict[str, object]] = [
            {"role": "user", "content": initial_user_content}
        ]
        output, call_log, _response = await self._run_anthropic_call(
            request=request,
            output_model=output_model,
            audit_store=audit_store,
            attempt=1,
            messages=messages,
            settings=settings,
            cache_enabled=cache_enabled,
        )
        return StructuredLLMResult[OutputModelT](output=output, call_log=call_log)

    async def _run_anthropic_call(
        self,
        *,
        request: StructuredLLMRequest,
        output_model: type[OutputModelT],
        audit_store: AuditStore | None,
        attempt: int,
        messages: list[dict[str, object]],
        settings: _ResolvedLLMSettings,
        cache_enabled: bool,
    ) -> tuple[OutputModelT, LLMCallLog, object]:
        anthropic_client = self._anthropic_client
        if anthropic_client is None:
            raise LLMClientError("Anthropic client is not configured")

        start = time.perf_counter()
        response = await anthropic_client.messages.create(
            model=settings.model,
            max_tokens=settings.max_output_tokens,
            temperature=self.config.temperature,
            system=_anthropic_system(request, cache_enabled=cache_enabled),
            messages=messages,
            tools=[
                _anthropic_tool_definition(
                    request,
                    output_model,
                    cache_enabled=cache_enabled,
                )
            ],
            tool_choice={"type": "tool", "name": request.tool_name},
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        call_log = _build_anthropic_call_log(
            request=request,
            response=response,
            model=settings.model,
            latency_ms=latency_ms,
            attempt=attempt,
        )
        if audit_store is not None:
            await audit_store.record_llm_call_log(call_log)

        tool_input = _extract_required_tool_input(response, request.tool_name)
        output = output_model.model_validate(tool_input)
        _print_llm_trace(request=request, output=output, call_log=call_log)
        return output, call_log, response

    async def complete_structured_with_retry(
        self,
        request: StructuredLLMRequest,
        *,
        output_model: type[OutputModelT],
        audit_store: AuditStore | None = None,
        validate: Callable[
            [OutputModelT], "Accepted[OutputModelT] | Complaints"
        ],
        merge: Callable[
            [OutputModelT, OutputModelT, frozenset[str]], OutputModelT
        ],
        max_retries: int = 1,
    ) -> StructuredLLMResult[OutputModelT]:
        if self.config.provider != "anthropic":
            raise NotImplementedError(
                "complete_structured_with_retry is only implemented for the Anthropic provider"
            )

        settings = _resolve_llm_settings(self.config, request.stage)
        cache_enabled = _anthropic_prompt_cache_enabled(self.config, request)
        initial_user_content = _anthropic_user_content(request, cache_enabled=cache_enabled)
        initial_messages: list[dict[str, object]] = [
            {"role": "user", "content": initial_user_content}
        ]

        output, call_log, response = await self._run_anthropic_call(
            request=request,
            output_model=output_model,
            audit_store=audit_store,
            attempt=1,
            messages=initial_messages,
            settings=settings,
            cache_enabled=cache_enabled,
        )

        for retry_index in range(max_retries):
            outcome = validate(output)
            if isinstance(outcome, Accepted):
                return StructuredLLMResult[OutputModelT](
                    output=output, call_log=call_log
                )
            if not outcome.complaints:
                return StructuredLLMResult[OutputModelT](
                    output=output, call_log=call_log
                )

            tool_use_id = _extract_tool_use_id(response, request.tool_name)
            assistant_blocks = _serialize_assistant_content(response)
            complaint_text = _format_complaint_payload(outcome.complaints)
            followup_messages: list[dict[str, object]] = [
                {"role": "user", "content": initial_user_content},
                {"role": "assistant", "content": assistant_blocks},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "is_error": True,
                            "content": complaint_text,
                        }
                    ],
                },
            ]

            retry_output, retry_call_log, retry_response = await self._run_anthropic_call(
                request=request,
                output_model=output_model,
                audit_store=audit_store,
                attempt=retry_index + 2,
                messages=followup_messages,
                settings=settings,
                cache_enabled=cache_enabled,
            )

            try:
                merged = merge(
                    output,
                    retry_output,
                    frozenset(c.identifier for c in outcome.complaints),
                )
            except LLMRetryMergeError:
                return StructuredLLMResult[OutputModelT](
                    output=output, call_log=call_log
                )

            output = merged
            call_log = retry_call_log
            response = retry_response

        return StructuredLLMResult[OutputModelT](output=output, call_log=call_log)

    async def _complete_openai(
        self,
        request: StructuredLLMRequest,
        *,
        output_model: type[OutputModelT],
        audit_store: AuditStore | None = None,
    ) -> StructuredLLMResult[OutputModelT]:
        openai_client = self._openai_client
        if openai_client is None:
            raise LLMClientError("OpenAI client is not configured")

        settings = _resolve_llm_settings(self.config, request.stage)
        create_kwargs = _build_openai_chat_kwargs(
            config=self.config,
            request=request,
            output_model=output_model,
            settings=settings,
        )

        start = time.perf_counter()
        response = await openai_client.chat.completions.create(**create_kwargs)
        latency_ms = int((time.perf_counter() - start) * 1000)
        call_log = _build_openai_call_log(
            request=request,
            response=response,
            model=settings.model,
            latency_ms=latency_ms,
            attempt=1,
        )
        if audit_store is not None:
            await audit_store.record_llm_call_log(call_log)

        tool_input = _extract_required_openai_tool_input(response, request.tool_name)
        output = output_model.model_validate(tool_input)
        _print_llm_trace(request=request, output=output, call_log=call_log)
        return StructuredLLMResult[OutputModelT](output=output, call_log=call_log)


def _create_anthropic_client(config: LLMConfig) -> object:
    try:
        from anthropic import AsyncAnthropic
    except ImportError as exc:
        raise LLMClientError(
            "The anthropic package is required to create an LLM client"
        ) from exc

    return AsyncAnthropic(max_retries=config.max_retries, timeout=config.timeout_seconds)


def _uses_openai_chat_client(config: LLMConfig) -> bool:
    return config.provider in _OPENAI_COMPATIBLE_PROVIDERS


def _resolve_llm_settings(config: LLMConfig, stage: LLMStage) -> _ResolvedLLMSettings:
    override = config.stage_overrides.get(_stage_group(stage))
    return _ResolvedLLMSettings(
        model=override.model if override and override.model is not None else config.model,
        max_output_tokens=(
            override.max_output_tokens
            if override and override.max_output_tokens is not None
            else config.max_output_tokens
        ),
        reasoning_effort=(
            override.reasoning_effort
            if override and override.reasoning_effort is not None
            else config.reasoning_effort
        ),
    )


def _anthropic_prompt_cache_enabled(
    config: LLMConfig,
    request: StructuredLLMRequest,
) -> bool:
    if not config.prompt_cache_enabled:
        return False
    if not request.prompt_cache_allowed:
        return False
    return (
        request.stable_user_prefix is not None
        or _stage_group(request.stage) in _ANTHROPIC_CACHEABLE_STAGE_GROUPS
    )


def _anthropic_system(
    request: StructuredLLMRequest,
    *,
    cache_enabled: bool,
) -> str | list[dict[str, object]]:
    if not cache_enabled:
        return request.prompt.text
    return [
        {
            "type": "text",
            "text": request.prompt.text,
            "cache_control": dict(_ANTHROPIC_EPHEMERAL_CACHE_CONTROL),
        }
    ]


def _anthropic_user_content(
    request: StructuredLLMRequest,
    *,
    cache_enabled: bool,
) -> str | list[dict[str, object]]:
    if not cache_enabled or request.stable_user_prefix is None:
        return request.full_user_content

    blocks: list[dict[str, object]] = [
        {
            "type": "text",
            "text": request.stable_user_prefix,
            "cache_control": dict(_ANTHROPIC_EPHEMERAL_CACHE_CONTROL),
        }
    ]
    if request.user_content:
        blocks.append({"type": "text", "text": request.user_content})
    return blocks


def _anthropic_tool_definition(
    request: StructuredLLMRequest,
    output_model: type[BaseModel],
    *,
    cache_enabled: bool,
) -> dict[str, object]:
    tool = {
        "name": request.tool_name,
        "description": request.tool_description,
        "input_schema": output_model.model_json_schema(),
    }
    if cache_enabled:
        tool["cache_control"] = dict(_ANTHROPIC_EPHEMERAL_CACHE_CONTROL)
    return tool


def _build_openai_chat_kwargs(
    *,
    config: LLMConfig,
    request: StructuredLLMRequest,
    output_model: type[BaseModel],
    settings: _ResolvedLLMSettings,
) -> dict[str, Any]:
    family = _openai_model_family(settings.model)
    kwargs: dict[str, Any] = {
        "model": settings.model,
        _token_limit_parameter(family): settings.max_output_tokens,
        "messages": _openai_messages(request),
        "tools": [_openai_tool_definition(request, output_model)],
        "tool_choice": _openai_tool_choice(request.tool_name),
        "parallel_tool_calls": False,
    }

    provider_options = _openai_provider_options(
        config=config,
        settings=settings,
        family=family,
    )
    kwargs.update(provider_options)
    return kwargs


def _openai_messages(request: StructuredLLMRequest) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": request.prompt.text},
        {"role": "user", "content": request.full_user_content},
    ]


def _openai_tool_definition(
    request: StructuredLLMRequest,
    output_model: type[BaseModel],
) -> dict[str, object]:
    return {
        "type": "function",
        "function": {
            "name": request.tool_name,
            "description": request.tool_description,
            "parameters": _openai_strict_tool_schema(output_model),
            "strict": True,
        },
    }


def _openai_tool_choice(tool_name: str) -> dict[str, object]:
    return {
        "type": "function",
        "function": {"name": tool_name},
    }


def _openai_provider_options(
    *,
    config: LLMConfig,
    settings: _ResolvedLLMSettings,
    family: _OpenAIModelFamily,
) -> dict[str, object]:
    if family.is_kimi:
        # Moonshot rejects named tool_choice with Kimi thinking enabled. The
        # structured-output invariant requires the named function call, so these
        # requests explicitly disable Kimi thinking.
        return {"extra_body": {"thinking": {"type": "disabled"}}}
    if family.is_reasoning:
        return {"reasoning_effort": settings.reasoning_effort}
    return {"temperature": config.temperature}


def _token_limit_parameter(family: _OpenAIModelFamily) -> str:
    return "max_tokens" if family.is_kimi else "max_completion_tokens"


def _openai_model_family(model: str) -> _OpenAIModelFamily:
    return _OpenAIModelFamily(
        is_reasoning=_is_openai_reasoning_model(model),
        is_kimi=_is_kimi_model(model),
    )


def _is_openai_reasoning_model(model: str) -> bool:
    name = model.lower()
    return (
        name.startswith("gpt-5")
        or name.startswith("o1")
        or name.startswith("o3")
        or name.startswith("o4")
    )


def _is_kimi_model(model: str) -> bool:
    return model.lower().startswith("kimi-")


def _create_openai_client(config: LLMConfig) -> object:
    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise LLMClientError(
            "The openai package is required to create an OpenAI client"
        ) from exc

    kwargs: dict[str, object] = {
        "max_retries": config.max_retries,
        "timeout": config.timeout_seconds,
    }
    if config.base_url is not None:
        kwargs["base_url"] = config.base_url
    if config.api_key_env is not None:
        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            raise LLMClientError(
                f"Missing API key environment variable: {config.api_key_env}"
            )
        kwargs["api_key"] = api_key

    return AsyncOpenAI(**kwargs)


def _openai_strict_tool_schema(output_model: type[BaseModel]) -> dict[str, Any]:
    schema = output_model.model_json_schema()
    _require_all_object_properties(schema)
    return schema


def _require_all_object_properties(schema: object) -> None:
    if isinstance(schema, dict):
        schema.pop("default", None)
        properties = schema.get("properties")
        if isinstance(properties, dict):
            schema["required"] = list(properties.keys())
            schema.setdefault("additionalProperties", False)
        for value in schema.values():
            _require_all_object_properties(value)
    elif isinstance(schema, list):
        for item in schema:
            _require_all_object_properties(item)


def _build_anthropic_call_log(
    *,
    request: StructuredLLMRequest,
    response: object,
    model: str,
    latency_ms: int,
    attempt: int,
) -> LLMCallLog:
    usage = _read_attr(response, "usage", {})
    return LLMCallLog(
        call_id=f"llm-{uuid.uuid4().hex}",
        run_id=request.run_id,
        stage=request.stage,
        attempt=attempt,
        model=model,
        prompt_sha256=request.prompt.sha256,
        input_tokens=_read_int(usage, "input_tokens"),
        output_tokens=_read_int(usage, "output_tokens"),
        cache_read_tokens=_read_int(usage, "cache_read_input_tokens", "cache_read_tokens"),
        cache_creation_tokens=_read_int(
            usage,
            "cache_creation_input_tokens",
            "cache_creation_tokens",
        ),
        latency_ms=max(latency_ms, 0),
        stop_reason=str(_read_attr(response, "stop_reason", "unknown")),
        tool_name=request.tool_name,
        created_at=datetime.now(timezone.utc),
    )


def _build_openai_call_log(
    *,
    request: StructuredLLMRequest,
    response: object,
    model: str,
    latency_ms: int,
    attempt: int,
) -> LLMCallLog:
    usage = _read_attr(response, "usage", {})
    prompt_details = _read_attr(usage, "prompt_tokens_details", {})
    choice = _first_choice(response)
    return LLMCallLog(
        call_id=f"llm-{uuid.uuid4().hex}",
        run_id=request.run_id,
        stage=request.stage,
        attempt=attempt,
        model=model,
        prompt_sha256=request.prompt.sha256,
        input_tokens=_read_int(usage, "prompt_tokens", "input_tokens"),
        output_tokens=_read_int(usage, "completion_tokens", "output_tokens"),
        cache_read_tokens=_read_int(prompt_details, "cached_tokens"),
        cache_creation_tokens=0,
        latency_ms=max(latency_ms, 0),
        stop_reason=str(_read_attr(choice, "finish_reason", "unknown")),
        tool_name=request.tool_name,
        created_at=datetime.now(timezone.utc),
    )


def _extract_tool_use_id(response: object, tool_name: str) -> str:
    content = _read_attr(response, "content", ())
    if not isinstance(content, list | tuple):
        raise LLMToolUseError("Anthropic response content must be a sequence")
    for block in content:
        if (
            _read_attr(block, "type", None) == "tool_use"
            and _read_attr(block, "name", None) == tool_name
        ):
            tool_use_id = _read_attr(block, "id", None)
            if not isinstance(tool_use_id, str) or not tool_use_id:
                raise LLMToolUseError(
                    f"tool_use block for {tool_name} is missing a string id"
                )
            return tool_use_id
    raise LLMToolUseError(
        f"Anthropic response did not include a tool_use block named {tool_name}"
    )


def _serialize_assistant_content(response: object) -> list[dict[str, object]]:
    content = _read_attr(response, "content", ())
    if not isinstance(content, list | tuple):
        return []
    blocks: list[dict[str, object]] = []
    for block in content:
        block_type = _read_attr(block, "type", None)
        if block_type == "tool_use":
            blocks.append(
                {
                    "type": "tool_use",
                    "id": _read_attr(block, "id", ""),
                    "name": _read_attr(block, "name", ""),
                    "input": _read_attr(block, "input", {}),
                }
            )
        elif block_type == "text":
            blocks.append(
                {
                    "type": "text",
                    "text": _read_attr(block, "text", ""),
                }
            )
    return blocks


def _format_complaint_payload(complaints: tuple[ItemComplaint, ...]) -> str:
    header = (
        f"Some items in your previous tool call failed validation. Re-emit ONLY the "
        f"following {len(complaints)} item(s), in this exact order, using the same "
        f"tool schema. Do not include any other items.\n\n"
    )
    body = "\n\n".join(complaint.message for complaint in complaints)
    return header + body


def _extract_required_tool_input(response: object, tool_name: str) -> Mapping[str, Any]:
    content = _read_attr(response, "content", ())
    if not isinstance(content, list | tuple):
        raise LLMToolUseError("Anthropic response content must be a sequence")

    tool_blocks = [
        block
        for block in content
        if _read_attr(block, "type", None) == "tool_use" and _read_attr(block, "name", None) == tool_name
    ]
    if len(tool_blocks) != 1:
        all_tool_names = [
            str(_read_attr(block, "name", ""))
            for block in content
            if _read_attr(block, "type", None) == "tool_use"
        ]
        if all_tool_names:
            raise LLMToolUseError(
                f"Expected tool_use named {tool_name}; received {', '.join(all_tool_names)}"
            )
        raise LLMToolUseError("Anthropic response did not include the required tool_use block")

    tool_input = _read_attr(tool_blocks[0], "input", None)
    if not isinstance(tool_input, Mapping):
        raise LLMToolUseError(f"Tool input for {tool_name} must be an object")
    return tool_input


def _extract_required_openai_tool_input(response: object, tool_name: str) -> Mapping[str, Any]:
    choice = _first_choice(response)
    message = _read_attr(choice, "message", None)
    if message is None:
        raise LLMToolUseError("OpenAI response did not include a message")

    tool_calls = _read_attr(message, "tool_calls", ())
    if tool_calls is None:
        tool_calls = ()
    if not isinstance(tool_calls, list | tuple):
        raise LLMToolUseError("OpenAI response tool_calls must be a sequence")

    matching_calls = []
    all_tool_names: list[str] = []
    for tool_call in tool_calls:
        function = _read_attr(tool_call, "function", None)
        name = str(_read_attr(function, "name", ""))
        if name:
            all_tool_names.append(name)
        if _read_attr(tool_call, "type", None) == "function" and name == tool_name:
            matching_calls.append(tool_call)

    if len(matching_calls) != 1:
        finish_reason = str(_read_attr(choice, "finish_reason", "unknown"))
        usage = _read_attr(response, "usage", None)
        completion_tokens = _read_int(usage, "completion_tokens", "output_tokens")
        details = _read_attr(usage, "completion_tokens_details", None)
        reasoning_tokens = _read_int(details, "reasoning_tokens")
        ctx = (
            f" [finish_reason={finish_reason}, completion_tokens={completion_tokens}"
            f", reasoning_tokens={reasoning_tokens}]"
        )
        hint = (
            " — for reasoning models this usually means max_completion_tokens was"
            " consumed by hidden reasoning before the tool call could be emitted;"
            " raise llm.max_output_tokens or lower reasoning_effort."
            if finish_reason == "length"
            else ""
        )
        if all_tool_names:
            raise LLMToolUseError(
                f"Expected OpenAI tool call named {tool_name}; received "
                + ", ".join(all_tool_names)
                + ctx
                + hint
            )
        raise LLMToolUseError(
            "OpenAI response did not include the required tool call" + ctx + hint
        )

    function = _read_attr(matching_calls[0], "function", None)
    raw_arguments = _read_attr(function, "arguments", None)
    if not isinstance(raw_arguments, str):
        raise LLMToolUseError(f"Tool arguments for {tool_name} must be a JSON object string")
    try:
        tool_input = json.loads(raw_arguments)
    except json.JSONDecodeError as exc:
        raise LLMToolUseError(f"Tool arguments for {tool_name} must be valid JSON") from exc
    if not isinstance(tool_input, Mapping):
        raise LLMToolUseError(f"Tool arguments for {tool_name} must decode to an object")
    return tool_input


def _first_choice(response: object) -> object:
    choices = _read_attr(response, "choices", ())
    if not isinstance(choices, list | tuple) or len(choices) != 1:
        raise LLMToolUseError("LLM response must include exactly one choice")
    return choices[0]


def _read_attr(value: object, name: str, default: object = None) -> object:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _read_int(value: object, *names: str) -> int:
    for name in names:
        raw_value = _read_attr(value, name, None)
        if raw_value is not None:
            return int(raw_value)
    return 0


__all__ = [
    "Accepted",
    "Complaints",
    "ItemComplaint",
    "LLMClient",
    "LLMClientError",
    "LLMRetryMergeError",
    "LLMToolUseError",
    "StructuredLLMRequest",
    "StructuredLLMResult",
]
