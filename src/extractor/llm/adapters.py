from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from pydantic import BaseModel

from extractor.config import LLMConfig
from extractor.contracts import LLMCallLog
from extractor.llm.errors import LLMClientError
from extractor.llm.models import StructuredLLMRequest
from extractor.llm.providers import (
    ResolvedLLMSettings,
    anthropic_prompt_cache_enabled,
    anthropic_system,
    anthropic_tool_definition,
    anthropic_user_content,
    build_openai_chat_kwargs,
)
from extractor.llm.responses import (
    build_anthropic_call_log,
    build_openai_call_log,
    extract_required_openai_tool_input,
    extract_required_tool_input,
)


class LLMProviderAdapter(Protocol):
    supports_retry: bool

    def build_request(
        self,
        *,
        config: LLMConfig,
        request: StructuredLLMRequest,
        output_model: type[BaseModel],
        settings: ResolvedLLMSettings,
        messages: list[dict[str, object]] | None = None,
        cache_enabled: bool | None = None,
    ) -> dict[str, Any]: ...

    async def send(self, provider_client: object, request_kwargs: dict[str, Any]) -> object: ...

    def extract_tool_input(
        self,
        response: object,
        tool_name: str,
    ) -> Mapping[str, Any]: ...

    def build_call_log(
        self,
        *,
        request: StructuredLLMRequest,
        response: object,
        model: str,
        latency_ms: int,
        attempt: int,
    ) -> LLMCallLog: ...


class AnthropicProviderAdapter:
    supports_retry = True

    def build_request(
        self,
        *,
        config: LLMConfig,
        request: StructuredLLMRequest,
        output_model: type[BaseModel],
        settings: ResolvedLLMSettings,
        messages: list[dict[str, object]] | None = None,
        cache_enabled: bool | None = None,
    ) -> dict[str, Any]:
        cache = (
            anthropic_prompt_cache_enabled(config, request)
            if cache_enabled is None
            else cache_enabled
        )
        call_messages = messages
        if call_messages is None:
            call_messages = [
                {
                    "role": "user",
                    "content": anthropic_user_content(request, cache_enabled=cache),
                }
            ]
        return {
            "model": settings.model,
            "max_tokens": settings.max_output_tokens,
            "temperature": config.temperature,
            "system": anthropic_system(request, cache_enabled=cache),
            "messages": call_messages,
            "tools": [
                anthropic_tool_definition(
                    request,
                    output_model,
                    cache_enabled=cache,
                )
            ],
            "tool_choice": {"type": "tool", "name": request.tool_name},
        }

    async def send(self, provider_client: object, request_kwargs: dict[str, Any]) -> object:
        messages_api = getattr(provider_client, "messages", None)
        if messages_api is None:
            raise LLMClientError("Anthropic client is not configured")
        return await messages_api.create(**request_kwargs)

    def extract_tool_input(
        self,
        response: object,
        tool_name: str,
    ) -> Mapping[str, Any]:
        return extract_required_tool_input(response, tool_name)

    def build_call_log(
        self,
        *,
        request: StructuredLLMRequest,
        response: object,
        model: str,
        latency_ms: int,
        attempt: int,
    ) -> LLMCallLog:
        return build_anthropic_call_log(
            request=request,
            response=response,
            model=model,
            latency_ms=latency_ms,
            attempt=attempt,
        )


class OpenAIChatProviderAdapter:
    supports_retry = False

    def build_request(
        self,
        *,
        config: LLMConfig,
        request: StructuredLLMRequest,
        output_model: type[BaseModel],
        settings: ResolvedLLMSettings,
        messages: list[dict[str, object]] | None = None,
        cache_enabled: bool | None = None,
    ) -> dict[str, Any]:
        return build_openai_chat_kwargs(
            config=config,
            request=request,
            output_model=output_model,
            settings=settings,
        )

    async def send(self, provider_client: object, request_kwargs: dict[str, Any]) -> object:
        chat_api = getattr(provider_client, "chat", None)
        completions_api = getattr(chat_api, "completions", None)
        if completions_api is None:
            raise LLMClientError("OpenAI client is not configured")
        return await completions_api.create(**request_kwargs)

    def extract_tool_input(
        self,
        response: object,
        tool_name: str,
    ) -> Mapping[str, Any]:
        return extract_required_openai_tool_input(response, tool_name)

    def build_call_log(
        self,
        *,
        request: StructuredLLMRequest,
        response: object,
        model: str,
        latency_ms: int,
        attempt: int,
    ) -> LLMCallLog:
        return build_openai_call_log(
            request=request,
            response=response,
            model=model,
            latency_ms=latency_ms,
            attempt=attempt,
        )


__all__ = [
    "AnthropicProviderAdapter",
    "LLMProviderAdapter",
    "OpenAIChatProviderAdapter",
]
