from __future__ import annotations

import asyncio
import hashlib
import os
import sys
from datetime import datetime, timezone
from typing import cast

from extractor.audit import AuditStore, CandidateRejection
from extractor.config import ExecutionConfig
from extractor.contracts import (
    Chunk,
    ExtractionPlan,
    LensCandidate,
    RejectionReason,
    SourceSpan,
)
from extractor.contracts.models import LLMStage, LensName
from extractor.llm import LLMClient, PromptLoader, StructuredLLMRequest
from extractor.executor.models import (
    ExecutionResult,
    ExecutorCandidateBatch,
    ExecutorStageInput,
    ExecutorTaskResult,
    ExtractedCandidatePayload,
)


class ExecutorError(RuntimeError):
    """Raised when executor inputs or budgets prevent auditable extraction."""


def _trace_enabled() -> bool:
    return os.environ.get("EXTRACTOR_LLM_TRACE", "1") not in {"0", "false", "False", ""}


def _print_executor_outcomes(
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


async def execute_plan(
    *,
    plan: ExtractionPlan,
    chunks: tuple[Chunk, ...],
    prompt_loader: PromptLoader,
    llm_client: LLMClient,
    execution_config: ExecutionConfig,
    audit_store: AuditStore | None = None,
) -> ExecutionResult:
    _validate_executor_inputs(plan, chunks)

    semaphore = asyncio.Semaphore(execution_config.max_chunk_concurrency)
    tasks = [
        _execute_lens_chunk(
            plan=plan,
            lens=lens,
            chunk=chunk,
            prompt_loader=prompt_loader,
            llm_client=llm_client,
            audit_store=audit_store,
            semaphore=semaphore,
        )
        for lens in plan.enabled_lenses
        for chunk in chunks
    ]
    results = await asyncio.gather(*tasks)

    return ExecutionResult(
        accepted_candidates=tuple(
            candidate for result in results for candidate in result.accepted_candidates
        ),
        rejected_candidates=tuple(
            candidate for result in results for candidate in result.rejected_candidates
        ),
        rejections=tuple(rejection for result in results for rejection in result.rejections),
    )


async def _execute_lens_chunk(
    *,
    plan: ExtractionPlan,
    lens: LensName,
    chunk: Chunk,
    prompt_loader: PromptLoader,
    llm_client: LLMClient,
    audit_store: AuditStore | None,
    semaphore: asyncio.Semaphore,
) -> ExecutorTaskResult:
    async with semaphore:
        stage = cast(LLMStage, f"executor.{lens}")
        result = await llm_client.complete_structured(
            StructuredLLMRequest(
                run_id=plan.run_id,
                stage=stage,
                prompt=prompt_loader.load(stage),
                user_content=ExecutorStageInput(
                    run_id=plan.run_id,
                    plan=plan,
                    lens=lens,
                    chunk=chunk,
                ).model_dump_json(),
                tool_name=f"extract_{lens}_candidates",
                tool_description=f"Extract {lens} candidates from one chunk.",
            ),
            output_model=ExecutorCandidateBatch,
            audit_store=audit_store,
        )

    accepted: list[LensCandidate] = []
    rejected: list[LensCandidate] = []
    rejections: list[CandidateRejection] = []
    outcomes: list[tuple[LensCandidate, tuple[RejectionReason, ...], int | None]] = []
    category_fields = _approved_category_fields(plan)

    for index, payload in enumerate(result.output.candidates):
        original_start_char = payload.start_char
        located = _locate_source_text(payload=payload, chunk=chunk)
        if located is not None and located != payload.start_char:
            payload = payload.model_copy(update={"start_char": located})
        candidate = _build_candidate(
            plan=plan,
            lens=lens,
            chunk=chunk,
            payload=payload,
            candidate_index=index,
            executor_call_id=result.call_log.call_id,
        )
        reasons = _candidate_rejection_reasons(
            payload=payload,
            candidate=candidate,
            chunk=chunk,
            category_fields=category_fields,
        )

        if audit_store is not None:
            await audit_store.record_lens_candidate(candidate)

        corrected_from = (
            original_start_char if payload.start_char != original_start_char else None
        )
        outcomes.append((candidate, tuple(reasons), corrected_from))

        if reasons:
            rejection = CandidateRejection(
                rejection_id=_stable_rejection_id(candidate, reasons),
                run_id=plan.run_id,
                candidate_id=candidate.candidate_id,
                stage="executor",
                reasons=tuple(reasons),
                created_at=datetime.now(timezone.utc),
            )
            if audit_store is not None:
                await audit_store.record_candidate_rejection(rejection)
            rejected.append(candidate)
            rejections.append(rejection)
        else:
            accepted.append(candidate)

    _print_executor_outcomes(
        lens=lens,
        chunk=chunk,
        call_id=result.call_log.call_id,
        outcomes=outcomes,
    )

    return ExecutorTaskResult(
        accepted_candidates=tuple(accepted),
        rejected_candidates=tuple(rejected),
        rejections=tuple(rejections),
    )


def _validate_executor_inputs(plan: ExtractionPlan, chunks: tuple[Chunk, ...]) -> None:
    if not chunks:
        raise ExecutorError("executor requires at least one chunk")
    for chunk in chunks:
        if chunk.doc_id != plan.doc_id:
            raise ExecutorError("chunk doc_id must match extraction plan doc_id")

    budgets = {budget.lens: budget.max_calls for budget in plan.budget.lens_budgets}
    for lens in plan.enabled_lenses:
        if len(chunks) > budgets[lens]:
            raise ExecutorError(
                f"executor budget for lens {lens} permits {budgets[lens]} calls, "
                f"but {len(chunks)} chunks require execution"
            )


def _build_candidate(
    *,
    plan: ExtractionPlan,
    lens: LensName,
    chunk: Chunk,
    payload: ExtractedCandidatePayload,
    candidate_index: int,
    executor_call_id: str,
) -> LensCandidate:
    end_char = payload.start_char + len(payload.source_text)
    start_byte, end_byte = _derive_byte_offsets(
        chunk=chunk,
        start_char=payload.start_char,
        source_text=payload.source_text,
    )
    source_span = SourceSpan(
        doc_id=plan.doc_id,
        chunk_id=chunk.chunk_id,
        start_char=payload.start_char,
        end_char=end_char,
        start_byte=start_byte,
        end_byte=end_byte,
        text=payload.source_text,
    )
    return LensCandidate(
        candidate_id=_stable_candidate_id(
            plan=plan,
            lens=lens,
            chunk=chunk,
            payload=payload,
            candidate_index=candidate_index,
        ),
        run_id=plan.run_id,
        doc_id=plan.doc_id,
        chunk_id=chunk.chunk_id,
        lens=lens,
        category=payload.category,
        field_name=payload.field_name,
        value=payload.value,
        source_span=source_span,
        confidence=payload.confidence,
        executor_call_id=executor_call_id,
    )


def _candidate_rejection_reasons(
    *,
    payload: ExtractedCandidatePayload,
    candidate: LensCandidate,
    chunk: Chunk,
    category_fields: dict[str, frozenset[str]],
) -> list[RejectionReason]:
    reasons: list[RejectionReason] = []
    fields = category_fields.get(candidate.category)
    if fields is None:
        reasons.append(
            RejectionReason(
                code="category_not_approved",
                message=f"Category is not approved for this extraction plan: {candidate.category}",
            )
        )
    elif candidate.field_name not in fields:
        reasons.append(
            RejectionReason(
                code="schema_violation",
                message=(
                    f"Field {candidate.field_name} is not approved for category "
                    f"{candidate.category}"
                ),
            )
        )

    offset_reason = _payload_offset_rejection_reason(payload=payload, chunk=chunk)
    if offset_reason is not None:
        reasons.append(offset_reason)

    if not _span_matches_chunk(candidate.source_span, chunk):
        reasons.append(
            RejectionReason(
                code="invented_span",
                message="Candidate source span does not match the chunk text at the provided offsets.",
            )
        )
    return reasons


_OFFSET_CORRECTION_WINDOW = 8


def _locate_source_text(
    *,
    payload: ExtractedCandidatePayload,
    chunk: Chunk,
) -> int | None:
    """Find the absolute start_char where source_text matches chunk text exactly.

    Tries the model's claimed start_char first. If that exact position doesn't
    match, searches a ±_OFFSET_CORRECTION_WINDOW window for a unique occurrence.
    Returns None if zero matches or more than one match in the window.
    """
    text = chunk.text
    source = payload.source_text
    if len(source) == 0:
        return None

    relative_claimed = payload.start_char - chunk.start_char
    if 0 <= relative_claimed and relative_claimed + len(source) <= len(text):
        if text[relative_claimed : relative_claimed + len(source)] == source:
            return payload.start_char

    search_start = max(0, relative_claimed - _OFFSET_CORRECTION_WINDOW)
    search_end = min(len(text), relative_claimed + _OFFSET_CORRECTION_WINDOW + len(source))
    if search_end - search_start < len(source):
        return None

    matches: list[int] = []
    cursor = search_start
    while cursor + len(source) <= search_end:
        idx = text.find(source, cursor, search_end)
        if idx < 0:
            break
        matches.append(idx)
        if len(matches) > 1:
            return None
        cursor = idx + 1

    if len(matches) == 1:
        return chunk.start_char + matches[0]
    return None


def _payload_offset_rejection_reason(
    *,
    payload: ExtractedCandidatePayload,
    chunk: Chunk,
) -> RejectionReason | None:
    relative_start = payload.start_char - chunk.start_char
    relative_end = relative_start + len(payload.source_text)
    if (
        relative_start < 0
        or relative_end > len(chunk.text)
        or len(payload.source_text) == 0
    ):
        return RejectionReason(
            code="invalid_source_offsets",
            message=(
                f"Candidate source_text length {len(payload.source_text)} at "
                f"start_char {payload.start_char} does not fit chunk "
                f"[{chunk.start_char}, {chunk.end_char})."
            ),
        )
    actual = chunk.text[relative_start:relative_end]
    if actual != payload.source_text:
        return RejectionReason(
            code="invalid_source_offsets",
            message=(
                "Candidate source_text does not match chunk slice at "
                f"start_char {payload.start_char}: expected "
                f"{payload.source_text!r}, found {actual!r}."
            ),
        )
    return None


def _derive_byte_offsets(
    *,
    chunk: Chunk,
    start_char: int,
    source_text: str,
) -> tuple[int, int]:
    # Caller must have already verified the slice; out-of-range slices return
    # (chunk.start_byte, chunk.start_byte) and are caught by _span_matches_chunk.
    relative_start = start_char - chunk.start_char
    if relative_start < 0 or relative_start > len(chunk.text):
        return chunk.start_byte, chunk.start_byte
    prefix_bytes = len(chunk.text[:relative_start].encode("utf-8"))
    text_bytes = len(source_text.encode("utf-8"))
    return chunk.start_byte + prefix_bytes, chunk.start_byte + prefix_bytes + text_bytes


def _span_matches_chunk(source_span: SourceSpan, chunk: Chunk) -> bool:
    if source_span.start_char < chunk.start_char or source_span.end_char > chunk.end_char:
        return False
    if source_span.start_byte < chunk.start_byte or source_span.end_byte > chunk.end_byte:
        return False

    relative_start_char = source_span.start_char - chunk.start_char
    relative_end_char = source_span.end_char - chunk.start_char
    relative_start_byte = source_span.start_byte - chunk.start_byte
    relative_end_byte = source_span.end_byte - chunk.start_byte
    chunk_bytes = chunk.text.encode("utf-8")
    return (
        chunk.text[relative_start_char:relative_end_char] == source_span.text
        and chunk_bytes[relative_start_byte:relative_end_byte] == source_span.text.encode("utf-8")
    )


def _approved_category_fields(plan: ExtractionPlan) -> dict[str, frozenset[str]]:
    return {
        category.name: frozenset(field.name for field in category.fields)
        for category in plan.approved_categories
    }


def _stable_candidate_id(
    *,
    plan: ExtractionPlan,
    lens: LensName,
    chunk: Chunk,
    payload: ExtractedCandidatePayload,
    candidate_index: int,
) -> str:
    identity = "|".join(
        (
            plan.run_id,
            plan.doc_id,
            chunk.chunk_id,
            lens,
            str(candidate_index),
            payload.category,
            payload.field_name,
            payload.value,
            str(payload.start_char),
            payload.source_text,
        )
    )
    return f"candidate-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


def _stable_rejection_id(
    candidate: LensCandidate,
    reasons: list[RejectionReason],
) -> str:
    reason_identity = "|".join(f"{reason.code}:{reason.message}" for reason in reasons)
    identity = f"{candidate.candidate_id}|{reason_identity}"
    return f"rejection-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


__all__ = ["ExecutorError", "execute_plan"]
