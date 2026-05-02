from __future__ import annotations

import os
import sys

from extractor.contracts import Chunk, LensCandidate, RejectionReason
from extractor.contracts.models import LensName


def print_executor_outcomes(
    *,
    lens: LensName,
    chunk: Chunk,
    call_id: str,
    outcomes: list[tuple[LensCandidate, tuple[RejectionReason, ...], int | None]],
) -> None:
    if not _trace_enabled() or not outcomes:
        return
    accepted = sum(1 for _, reasons, _ in outcomes if not reasons)
    rejected = len(outcomes) - accepted
    corrected = sum(1 for _, _, corrected_from in outcomes if corrected_from is not None)
    lines = [
        "",
        f" -> EXECUTOR.OUTCOMES | lens={lens} chunk={chunk.chunk_id} call={call_id} "
        f"accepted={accepted} rejected={rejected} corrected={corrected}",
    ]
    for candidate, reasons, corrected_from in outcomes:
        verdict = "PASS" if not reasons else "REJECT"
        snippet = candidate.source_span.text.replace("\n", " ")
        if len(snippet) > 80:
            snippet = snippet[:77] + "..."
        suffix = (
            f"  (auto-corrected from @{corrected_from})"
            if corrected_from is not None
            else ""
        )
        head = (
            f"   [{verdict}] {candidate.candidate_id} "
            f"{candidate.category}.{candidate.field_name} "
            f"@{candidate.source_span.start_char} {snippet!r}{suffix}"
        )
        lines.append(head)
        for reason in reasons:
            lines.append(f"          - {reason.code}: {reason.message}")
    print("\n".join(lines), file=sys.stderr, flush=True)


def _trace_enabled() -> bool:
    return os.environ.get("EXTRACTOR_LLM_TRACE", "1") not in {"0", "false", "False", ""}


__all__ = ["print_executor_outcomes"]
