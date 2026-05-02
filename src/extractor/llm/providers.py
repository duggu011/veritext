from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from extractor.config import LLMConfig
from extractor.contracts.models import LLMStage
from extractor.llm.errors import LLMClientError
from extractor.llm.models import StructuredLLMRequest
from extractor.llm.trace import stage_group


OPENAI_COMPATIBLE_PROVIDERS = {"openai", "openai_compatible"}
ANTHROPIC_CACHEABLE_STAGE_GROUPS = {"planner", "executor", "critic", "verifier"}
ANTHROPIC_EPHEMERAL_CACHE_CONTROL = {"type": "ephemeral"}


@dataclass(frozen=True)
class ResolvedLLMSettings:
    model: str
    max_output_tokens: int
    reasoning_effort: str


@dataclass(frozen=True)
class OpenAIModelFamily:
    is_reasoning: bool
    is_kimi: bool


def create_anthropic_client(config: LLMConfig) -> object:
    try:
        from anthropic import AsyncAnthropic
    except ImportError as exc:
        raise LLMClientError(
            "The anthropic package is required to create an LLM client"
        ) from exc

    return AsyncAnthropic(max_retries=config.max_retries, timeout=config.timeout_seconds)


def create_openai_client(config: LLMConfig) -> object:
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


def uses_openai_chat_client(config: LLMConfig) -> bool:
    return config.provider in OPENAI_COMPATIBLE_PROVIDERS


def resolve_llm_settings(config: LLMConfig, stage: LLMStage) -> ResolvedLLMSettings:
    override = config.stage_overrides.get(stage_group(stage))
    return ResolvedLLMSettings(
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


def anthropic_prompt_cache_enabled(
    config: LLMConfig,
    request: StructuredLLMRequest,
) -> bool:
    if not config.prompt_cache_enabled:
        return False
    if not request.prompt_cache_allowed:
        return False
    return (
        request.stable_user_prefix is not None
        or stage_group(request.stage) in ANTHROPIC_CACHEABLE_STAGE_GROUPS
    )


def anthropic_system(
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
            "cache_control": dict(ANTHROPIC_EPHEMERAL_CACHE_CONTROL),
        }
    ]


def anthropic_user_content(
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
            "cache_control": dict(ANTHROPIC_EPHEMERAL_CACHE_CONTROL),
        }
    ]
    if request.user_content:
        blocks.append({"type": "text", "text": request.user_content})
    return blocks


def anthropic_tool_definition(
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
        tool["cache_control"] = dict(ANTHROPIC_EPHEMERAL_CACHE_CONTROL)
    return tool


def build_openai_chat_kwargs(
    *,
    config: LLMConfig,
    request: StructuredLLMRequest,
    output_model: type[BaseModel],
    settings: ResolvedLLMSettings,
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
    settings: ResolvedLLMSettings,
    family: OpenAIModelFamily,
) -> dict[str, object]:
    if family.is_kimi:
        # Moonshot rejects named tool_choice with Kimi thinking enabled. The
        # structured-output invariant requires the named function call, so these
        # requests explicitly disable Kimi thinking.
        return {"extra_body": {"thinking": {"type": "disabled"}}}
    if family.is_reasoning:
        return {"reasoning_effort": settings.reasoning_effort}
    return {"temperature": config.temperature}


def _token_limit_parameter(family: OpenAIModelFamily) -> str:
    return "max_tokens" if family.is_kimi else "max_completion_tokens"


def _openai_model_family(model: str) -> OpenAIModelFamily:
    return OpenAIModelFamily(
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


__all__ = [
    "ResolvedLLMSettings",
    "anthropic_prompt_cache_enabled",
    "anthropic_system",
    "anthropic_tool_definition",
    "anthropic_user_content",
    "build_openai_chat_kwargs",
    "create_anthropic_client",
    "create_openai_client",
    "resolve_llm_settings",
    "uses_openai_chat_client",
]
