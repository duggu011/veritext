from __future__ import annotations

import asyncio
import time

from collections.abc import Awaitable, Callable

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
from extractor.llm.adapters import (
    AnthropicProviderAdapter,
    LLMProviderAdapter,
    OpenAIChatProviderAdapter,
)
from extractor.llm.providers import (
    anthropic_prompt_cache_enabled,
    anthropic_user_content,
    create_anthropic_client,
    create_openai_client,
    resolve_llm_settings,
    uses_openai_chat_client,
)
from extractor.llm.responses import (
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
        self._provider_adapter, self._provider_client = self._select_provider()

    def _select_provider(self) -> tuple[LLMProviderAdapter, object | None]:
        if self.config.provider == "anthropic":
            return AnthropicProviderAdapter(), self._anthropic_client
        if uses_openai_chat_client(self.config):
            return OpenAIChatProviderAdapter(), self._openai_client
        return OpenAIChatProviderAdapter(), None

    async def complete_structured(
        self,
        request: StructuredLLMRequest,
        *,
        output_model: type[OutputModelT],
        audit_store: AuditStore | None = None,
    ) -> StructuredLLMResult[OutputModelT]:
        output, call_log, _response = await self._run_provider_call(
            request=request,
            output_model=output_model,
            audit_store=audit_store,
            attempt=1,
        )
        return StructuredLLMResult[OutputModelT](output=output, call_log=call_log)

    async def _run_provider_call(
        self,
        *,
        request: StructuredLLMRequest,
        output_model: type[OutputModelT],
        audit_store: AuditStore | None,
        attempt: int,
        messages: list[dict[str, object]] | None = None,
        cache_enabled: bool | None = None,
    ) -> tuple[OutputModelT, LLMCallLog, object]:
        provider_client = self._provider_client
        if provider_client is None:
            raise LLMClientError(f"Unsupported LLM provider: {self.config.provider}")

        settings = resolve_llm_settings(self.config, request.stage)
        request_kwargs = self._provider_adapter.build_request(
            config=self.config,
            request=request,
            output_model=output_model,
            settings=settings,
            messages=messages,
            cache_enabled=cache_enabled,
        )
        await self._throttle_request_start()
        start = time.perf_counter()
        response = await self._provider_adapter.send(provider_client, request_kwargs)
        latency_ms = int((time.perf_counter() - start) * 1000)
        call_log = self._provider_adapter.build_call_log(
            request=request,
            response=response,
            model=settings.model,
            latency_ms=latency_ms,
            attempt=attempt,
        )
        if audit_store is not None:
            await audit_store.record_llm_call_log(call_log)

        tool_input = self._provider_adapter.extract_tool_input(
            response,
            request.tool_name,
        )
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
        if not self._provider_adapter.supports_retry:
            raise NotImplementedError(
                "complete_structured_with_retry is only implemented for the Anthropic provider"
            )

        cache_enabled = anthropic_prompt_cache_enabled(self.config, request)
        initial_user_content = anthropic_user_content(
            request,
            cache_enabled=cache_enabled,
        )
        initial_messages: list[dict[str, object]] = [
            {"role": "user", "content": initial_user_content}
        ]

        output, call_log, response = await self._run_provider_call(
            request=request,
            output_model=output_model,
            audit_store=audit_store,
            attempt=1,
            messages=initial_messages,
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

            retry_output, retry_call_log, retry_response = await self._run_provider_call(
                request=request,
                output_model=output_model,
                audit_store=audit_store,
                attempt=retry_index + 2,
                messages=followup_messages,
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
