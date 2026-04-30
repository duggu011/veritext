from __future__ import annotations

import asyncio
import hashlib
import os
import sys
from dataclasses import dataclass
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


@dataclass(frozen=True)
class SourceTextResolution:
    start_char: int
    source_text: str
    rejection_reasons: tuple[RejectionReason, ...] = ()


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
        resolution = _resolve_source_text(payload=payload, chunk=chunk)
        if (
            resolution.start_char != payload.start_char
            or resolution.source_text != payload.source_text
        ):
            payload = payload.model_copy(
                update={
                    "start_char": resolution.start_char,
                    "source_text": resolution.source_text,
                }
            )
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
        reasons = [*resolution.rejection_reasons, *reasons]

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


_SHORT_AMBIGUOUS_SPAN_MAX_CHARS = 24


def _resolve_source_text(
    *,
    payload: ExtractedCandidatePayload,
    chunk: Chunk,
) -> SourceTextResolution:
    """Find the safest chunk-backed span for source_text.

    Exact unique matches are preferred. If exact text is absent, a unique
    whitespace-normalized match is allowed, but the source span is rewritten to
    the exact chunk substring so downstream provenance remains byte-for-byte.
    """
    text = chunk.text
    source = payload.source_text
    if len(source) == 0:
        return SourceTextResolution(
            start_char=payload.start_char,
            source_text=payload.source_text,
        )

    relative_claimed = payload.start_char - chunk.start_char
    exact_matches = _find_exact_matches(text, source)
    if relative_claimed in exact_matches:
        rejection_reasons = (
            (_ambiguous_source_span_reason(source, len(exact_matches)))
            if _is_short_ambiguous_source(source, exact_matches)
            else ()
        )
        return SourceTextResolution(
            start_char=payload.start_char,
            source_text=payload.source_text,
            rejection_reasons=rejection_reasons,
        )
    if len(exact_matches) == 1:
        return SourceTextResolution(
            start_char=chunk.start_char + exact_matches[0],
            source_text=source,
        )

    stripped = source.strip()
    if stripped and stripped != source:
        stripped_matches = _find_exact_matches(text, stripped)
        if len(stripped_matches) == 1:
            return SourceTextResolution(
                start_char=chunk.start_char + stripped_matches[0],
                source_text=stripped,
            )

    normalized_matches = _find_whitespace_normalized_matches(text, source)
    if len(normalized_matches) == 1:
        start, end = normalized_matches[0]
        return SourceTextResolution(
            start_char=chunk.start_char + start,
            source_text=text[start:end],
        )

    return SourceTextResolution(
        start_char=payload.start_char,
        source_text=payload.source_text,
    )


def _find_exact_matches(text: str, source: str) -> list[int]:
    matches: list[int] = []
    cursor = 0
    while cursor + len(source) <= len(text):
        idx = text.find(source, cursor)
        if idx < 0:
            break
        matches.append(idx)
        cursor = idx + 1
    return matches


def _is_short_ambiguous_source(source: str, matches: list[int]) -> bool:
    return len(matches) > 1 and len(source) <= _SHORT_AMBIGUOUS_SPAN_MAX_CHARS


def _ambiguous_source_span_reason(
    source: str,
    match_count: int,
) -> tuple[RejectionReason, ...]:
    return (
        RejectionReason(
            code="ambiguous_source_span",
            message=(
                f"Candidate source_text {source!r} appears {match_count} times in "
                "the chunk; emit a wider unique source_text to preserve provenance."
            ),
        ),
    )


def _find_whitespace_normalized_matches(
    text: str,
    source: str,
) -> list[tuple[int, int]]:
    normalized_source = _collapse_whitespace(source)
    if normalized_source == "" or not any(char.isspace() for char in source):
        return []

    normalized_text, mapping = _normalize_whitespace_with_mapping(text)
    matches: list[tuple[int, int]] = []
    cursor = 0
    while cursor + len(normalized_source) <= len(normalized_text):
        idx = normalized_text.find(normalized_source, cursor)
        if idx < 0:
            break
        start = mapping[idx]
        end = mapping[idx + len(normalized_source) - 1] + 1
        matches.append((start, end))
        cursor = idx + 1
    return matches


def _collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


def _normalize_whitespace_with_mapping(text: str) -> tuple[str, list[int]]:
    normalized: list[str] = []
    mapping: list[int] = []
    in_whitespace = False
    for index, char in enumerate(text):
        if char.isspace():
            if normalized and not in_whitespace:
                normalized.append(" ")
                mapping.append(index)
            in_whitespace = True
            continue
        normalized.append(char)
        mapping.append(index)
        in_whitespace = False

    if normalized and normalized[-1] == " ":
        normalized.pop()
        mapping.pop()
    return "".join(normalized), mapping


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
