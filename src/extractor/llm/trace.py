from __future__ import annotations

import os
import sys

from pydantic import BaseModel

from extractor.contracts import LLMCallLog
from extractor.contracts.models import LLMStage
from extractor.llm.models import StructuredLLMRequest


# Visual divider widths for the human-readable LLM trace lines.
_TRACE_OUTER = "=" * 100
_TRACE_INNER = "-" * 100
# Per-section character cap so giant prompts/payloads stay readable in a terminal.
_TRACE_MAX_SECTION_CHARS = 4000


def print_llm_trace(
    *,
    request: StructuredLLMRequest,
    output: BaseModel,
    call_log: LLMCallLog,
) -> None:
    if not _trace_enabled():
        return
    group = stage_group(request.stage)
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


def stage_group(stage: LLMStage) -> str:
    return stage.split(".", 1)[0]


def _trace_enabled() -> bool:
    # Default the trace to ON. Set EXTRACTOR_LLM_TRACE=0 to silence it.
    # Name avoids the VERITEXT_ prefix so the config loader doesn't try to bind it.
    return os.environ.get("EXTRACTOR_LLM_TRACE", "1") not in {"0", "false", "False", ""}


def _truncate_for_trace(text: str) -> str:
    if len(text) <= _TRACE_MAX_SECTION_CHARS:
        return text
    head = text[:_TRACE_MAX_SECTION_CHARS]
    return f"{head}\n... [truncated {len(text) - _TRACE_MAX_SECTION_CHARS} chars] ..."


__all__ = ["print_llm_trace", "stage_group"]
