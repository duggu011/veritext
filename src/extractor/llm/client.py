from __future__ import annotations

import asyncio
import time

from collections.abc import Awaitable, Callable

from pydantic import BaseModel

from extractor.audit import AuditStore
from extractor.config import LLMConfig
from extractor.contracts import LLMCallLog
from extractor.llm.errors import LLMClientError, LLMRetryMergeError, LLMToolUseError
from extractor.llm.models import (
    Accepted,
    Complaints,
    ItemComplaint,
    OutputModelT,
    StructuredLLMRequest,
    StructuredLLMResult,
)
from extractor.llm.providers import (
    ResolvedLLMSettings,
    anthropic_prompt_cache_enabled,
    anthropic_system,
    anthropic_tool_definition,
    anthropic_user_content,
    build_openai_chat_kwargs,
    create_anthropic_client,
    create_openai_client,
    resolve_llm_settings,
    uses_openai_chat_client,
)
from extractor.llm.responses import (
    build_anthropic_call_log,
    build_openai_call_log,
    extract_required_openai_tool_input,
    extract_required_tool_input,
    extract_tool_use_id,
    format_complaint_payload,
    serialize_assistant_content,
)
from extractor.llm.trace import print_llm_trace


class LLMClient:
    def __init__(
        self,
        config: LLMConfig,
        *,
        anthropic_client: object | None = None,
        openai_client: object | None = None,
        monotonic: Callable[[], float] | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self.config = config
        self._request_lock = asyncio.Lock()
        self._last_request_started_at: float | None = None
        self._monotonic = monotonic or time.monotonic
        self._sleep = sleep or asyncio.sleep
        self._anthropic_client = (
            anthropic_client if config.provider == "anthropic" else None
        )
        self._openai_client = (
            openai_client if uses_openai_chat_client(config) else None
        )
        if config.provider == "anthropic" and self._anthropic_client is None:
            self._anthropic_client = create_anthropic_client(config)
        if uses_openai_chat_client(config) and self._openai_client is None:
            self._openai_client = create_openai_client(config)

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
        if uses_openai_chat_client(self.config):
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
        settings = resolve_llm_settings(self.config, request.stage)
        cache_enabled = anthropic_prompt_cache_enabled(self.config, request)
        initial_user_content = anthropic_user_content(
            request,
            cache_enabled=cache_enabled,
        )
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
        settings: ResolvedLLMSettings,
        cache_enabled: bool,
    ) -> tuple[OutputModelT, LLMCallLog, object]:
        anthropic_client = self._anthropic_client
        if anthropic_client is None:
            raise LLMClientError("Anthropic client is not configured")

        await self._throttle_request_start()
        start = time.perf_counter()
        response = await anthropic_client.messages.create(
            model=settings.model,
            max_tokens=settings.max_output_tokens,
            temperature=self.config.temperature,
            system=anthropic_system(request, cache_enabled=cache_enabled),
            messages=messages,
            tools=[
                anthropic_tool_definition(
                    request,
                    output_model,
                    cache_enabled=cache_enabled,
                )
            ],
            tool_choice={"type": "tool", "name": request.tool_name},
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        call_log = build_anthropic_call_log(
            request=request,
            response=response,
            model=settings.model,
            latency_ms=latency_ms,
            attempt=attempt,
        )
        if audit_store is not None:
            await audit_store.record_llm_call_log(call_log)

        tool_input = extract_required_tool_input(response, request.tool_name)
        output = output_model.model_validate(tool_input)
        print_llm_trace(request=request, output=output, call_log=call_log)
        return output, call_log, response

    async def complete_structured_with_retry(
        self,
        request: StructuredLLMRequest,
        *,
        output_model: type[OutputModelT],
        audit_store: AuditStore | None = None,
        validate: Callable[[OutputModelT], Accepted[OutputModelT] | Complaints],
        merge: Callable[
            [OutputModelT, OutputModelT, frozenset[str]], OutputModelT
        ],
        max_retries: int = 1,
    ) -> StructuredLLMResult[OutputModelT]:
        if self.config.provider != "anthropic":
            raise NotImplementedError(
                "complete_structured_with_retry is only implemented for the Anthropic provider"
            )

        settings = resolve_llm_settings(self.config, request.stage)
        cache_enabled = anthropic_prompt_cache_enabled(self.config, request)
        initial_user_content = anthropic_user_content(
            request,
            cache_enabled=cache_enabled,
        )
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
                    output=output,
                    call_log=call_log,
                )
            if not outcome.complaints:
                return StructuredLLMResult[OutputModelT](
                    output=output,
                    call_log=call_log,
                )

            tool_use_id = extract_tool_use_id(response, request.tool_name)
            assistant_blocks = serialize_assistant_content(response)
            complaint_text = format_complaint_payload(outcome.complaints)
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
                    output=output,
                    call_log=call_log,
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

        settings = resolve_llm_settings(self.config, request.stage)
        create_kwargs = build_openai_chat_kwargs(
            config=self.config,
            request=request,
            output_model=output_model,
            settings=settings,
        )

        await self._throttle_request_start()
        start = time.perf_counter()
        response = await openai_client.chat.completions.create(**create_kwargs)
        latency_ms = int((time.perf_counter() - start) * 1000)
        call_log = build_openai_call_log(
            request=request,
            response=response,
            model=settings.model,
            latency_ms=latency_ms,
            attempt=1,
        )
        if audit_store is not None:
            await audit_store.record_llm_call_log(call_log)

        tool_input = extract_required_openai_tool_input(response, request.tool_name)
        output = output_model.model_validate(tool_input)
        print_llm_trace(request=request, output=output, call_log=call_log)
        return StructuredLLMResult[OutputModelT](output=output, call_log=call_log)

    async def _throttle_request_start(self) -> None:
        interval = self.config.min_request_interval_seconds
        if interval <= 0:
            return

        async with self._request_lock:
            now = self._monotonic()
            if self._last_request_started_at is not None:
                elapsed = now - self._last_request_started_at
                remaining = interval - elapsed
                if remaining > 0:
                    await self._sleep(remaining)
                    now = self._monotonic()
            self._last_request_started_at = now


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
