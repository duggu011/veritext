from __future__ import annotations

import os
import sys


_STAGE_BANNER = "#" * 100


def print_stage(name: str, detail: str = "") -> None:
    if not _stage_trace_enabled():
        return
    suffix = f"  | {detail}" if detail else ""
    print(
        f"\n{_STAGE_BANNER}\n  -> {name.upper()}{suffix}\n{_STAGE_BANNER}",
        file=sys.stderr,
        flush=True,
    )


def _stage_trace_enabled() -> bool:
    # Mirrors the LLM trace toggle so a single env switch silences both.
    return os.environ.get("EXTRACTOR_LLM_TRACE", "1") not in {"0", "false", "False", ""}


__all__ = ["print_stage"]
