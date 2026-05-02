from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from extractor.contracts import LLMCallLog
from extractor.llm.errors import LLMToolUseError
from extractor.llm.models import ItemComplaint, StructuredLLMRequest


def build_anthropic_call_log(
    *,
    request: StructuredLLMRequest,
    response: object,
    model: str,
    latency_ms: int,
    attempt: int,
) -> LLMCallLog:
    usage = read_attr(response, "usage", {})
    return LLMCallLog(
        call_id=f"llm-{uuid.uuid4().hex}",
        run_id=request.run_id,
        stage=request.stage,
        attempt=attempt,
        model=model,
        prompt_sha256=request.prompt.sha256,
        input_tokens=read_int(usage, "input_tokens"),
        output_tokens=read_int(usage, "output_tokens"),
        cache_read_tokens=read_int(usage, "cache_read_input_tokens", "cache_read_tokens"),
        cache_creation_tokens=read_int(
            usage,
            "cache_creation_input_tokens",
            "cache_creation_tokens",
        ),
        latency_ms=max(latency_ms, 0),
        stop_reason=str(read_attr(response, "stop_reason", "unknown")),
        tool_name=request.tool_name,
        created_at=datetime.now(timezone.utc),
    )


def build_openai_call_log(
    *,
    request: StructuredLLMRequest,
    response: object,
    model: str,
    latency_ms: int,
    attempt: int,
) -> LLMCallLog:
    usage = read_attr(response, "usage", {})
    prompt_details = read_attr(usage, "prompt_tokens_details", {})
    choice = first_choice(response)
    return LLMCallLog(
        call_id=f"llm-{uuid.uuid4().hex}",
        run_id=request.run_id,
        stage=request.stage,
        attempt=attempt,
        model=model,
        prompt_sha256=request.prompt.sha256,
        input_tokens=read_int(usage, "prompt_tokens", "input_tokens"),
        output_tokens=read_int(usage, "completion_tokens", "output_tokens"),
        cache_read_tokens=read_int(prompt_details, "cached_tokens"),
        cache_creation_tokens=0,
        latency_ms=max(latency_ms, 0),
        stop_reason=str(read_attr(choice, "finish_reason", "unknown")),
        tool_name=request.tool_name,
        created_at=datetime.now(timezone.utc),
    )


def extract_tool_use_id(response: object, tool_name: str) -> str:
    content = read_attr(response, "content", ())
    if not isinstance(content, list | tuple):
        raise LLMToolUseError("Anthropic response content must be a sequence")
    for block in content:
        if (
            read_attr(block, "type", None) == "tool_use"
            and read_attr(block, "name", None) == tool_name
        ):
            tool_use_id = read_attr(block, "id", None)
            if not isinstance(tool_use_id, str) or not tool_use_id:
                raise LLMToolUseError(
                    f"tool_use block for {tool_name} is missing a string id"
                )
            return tool_use_id
    raise LLMToolUseError(
        f"Anthropic response did not include a tool_use block named {tool_name}"
    )


def serialize_assistant_content(response: object) -> list[dict[str, object]]:
    content = read_attr(response, "content", ())
    if not isinstance(content, list | tuple):
        return []
    blocks: list[dict[str, object]] = []
    for block in content:
        block_type = read_attr(block, "type", None)
        if block_type == "tool_use":
            blocks.append(
                {
                    "type": "tool_use",
                    "id": read_attr(block, "id", ""),
                    "name": read_attr(block, "name", ""),
                    "input": read_attr(block, "input", {}),
                }
            )
        elif block_type == "text":
            blocks.append(
                {
                    "type": "text",
                    "text": read_attr(block, "text", ""),
                }
            )
    return blocks


def format_complaint_payload(complaints: tuple[ItemComplaint, ...]) -> str:
    header = (
        f"Some items in your previous tool call failed validation. Re-emit ONLY the "
        f"following {len(complaints)} item(s), in this exact order, using the same "
        f"tool schema. Do not include any other items.\n\n"
    )
    body = "\n\n".join(complaint.message for complaint in complaints)
    return header + body


def extract_required_tool_input(response: object, tool_name: str) -> Mapping[str, Any]:
    content = read_attr(response, "content", ())
    if not isinstance(content, list | tuple):
        raise LLMToolUseError("Anthropic response content must be a sequence")

    tool_blocks = [
        block
        for block in content
        if read_attr(block, "type", None) == "tool_use" and read_attr(block, "name", None) == tool_name
    ]
    if len(tool_blocks) != 1:
        all_tool_names = [
            str(read_attr(block, "name", ""))
            for block in content
            if read_attr(block, "type", None) == "tool_use"
        ]
        if all_tool_names:
            raise LLMToolUseError(
                f"Expected tool_use named {tool_name}; received {', '.join(all_tool_names)}"
            )
        raise LLMToolUseError("Anthropic response did not include the required tool_use block")

    tool_input = read_attr(tool_blocks[0], "input", None)
    if not isinstance(tool_input, Mapping):
        raise LLMToolUseError(f"Tool input for {tool_name} must be an object")
    return tool_input


def extract_required_openai_tool_input(response: object, tool_name: str) -> Mapping[str, Any]:
    choice = first_choice(response)
    message = read_attr(choice, "message", None)
    if message is None:
        raise LLMToolUseError("OpenAI response did not include a message")

    tool_calls = read_attr(message, "tool_calls", ())
    if tool_calls is None:
        tool_calls = ()
    if not isinstance(tool_calls, list | tuple):
        raise LLMToolUseError("OpenAI response tool_calls must be a sequence")

    matching_calls = []
    all_tool_names: list[str] = []
    for tool_call in tool_calls:
        function = read_attr(tool_call, "function", None)
        name = str(read_attr(function, "name", ""))
        if name:
            all_tool_names.append(name)
        if read_attr(tool_call, "type", None) == "function" and name == tool_name:
            matching_calls.append(tool_call)

    if len(matching_calls) != 1:
        finish_reason = str(read_attr(choice, "finish_reason", "unknown"))
        usage = read_attr(response, "usage", None)
        completion_tokens = read_int(usage, "completion_tokens", "output_tokens")
        details = read_attr(usage, "completion_tokens_details", None)
        reasoning_tokens = read_int(details, "reasoning_tokens")
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

    function = read_attr(matching_calls[0], "function", None)
    raw_arguments = read_attr(function, "arguments", None)
    if not isinstance(raw_arguments, str):
        raise LLMToolUseError(f"Tool arguments for {tool_name} must be a JSON object string")
    try:
        tool_input = json.loads(raw_arguments)
    except json.JSONDecodeError as exc:
        raise LLMToolUseError(f"Tool arguments for {tool_name} must be valid JSON") from exc
    if not isinstance(tool_input, Mapping):
        raise LLMToolUseError(f"Tool arguments for {tool_name} must decode to an object")
    return tool_input


def first_choice(response: object) -> object:
    choices = read_attr(response, "choices", ())
    if not isinstance(choices, list | tuple) or len(choices) != 1:
        raise LLMToolUseError("LLM response must include exactly one choice")
    return choices[0]


def read_attr(value: object, name: str, default: object = None) -> object:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def read_int(value: object, *names: str) -> int:
    for name in names:
        raw_value = read_attr(value, name, None)
        if raw_value is not None:
            return int(raw_value)
    return 0


__all__ = [
    "build_anthropic_call_log",
    "build_openai_call_log",
    "extract_required_openai_tool_input",
    "extract_required_tool_input",
    "extract_tool_use_id",
    "format_complaint_payload",
    "serialize_assistant_content",
]
