from __future__ import annotations

import asyncio
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
from extractor.llm import (
    Accepted,
    Complaints,
    ItemComplaint,
    LLMClient,
    LLMRetryMergeError,
    PromptLoader,
    StructuredLLMRequest,
)
from extractor.llm.payloads import split_model_json_before_field
from extractor.llm.views import chunk_view_from_chunk, schema_card_from_plan
from extractor.executor.errors import ExecutorError
from extractor.executor.ids import stable_rejection_id
from extractor.executor.materialization import build_candidate
from extractor.executor.models import (
    ExecutionResult,
    ExecutorCandidateBatch,
    ExecutorStageInput,
    ExecutorTaskResult,
    ExtractedCandidatePayload,
)
from extractor.executor.normalization import prepare_candidate_payload
from extractor.executor.payload_expansion import expand_candidate_payloads
from extractor.executor.trace import print_executor_outcomes
from extractor.executor.validation import validate_executor_inputs


async def execute_plan(
    *,
    plan: ExtractionPlan,
    chunks: tuple[Chunk, ...],
    prompt_loader: PromptLoader,
    llm_client: LLMClient,
    execution_config: ExecutionConfig,
    audit_store: AuditStore | None = None,
) -> ExecutionResult:
    validate_executor_inputs(plan, chunks)

    semaphore = asyncio.Semaphore(execution_config.max_chunk_concurrency)
    prompt_cache_allowed = len(chunks) > 1
    max_retries = max(execution_config.max_llm_attempts - 1, 0)
    tasks = [
        _execute_lens_chunk(
            plan=plan,
            lens=lens,
            chunk=chunk,
            prompt_cache_allowed=prompt_cache_allowed,
            prompt_loader=prompt_loader,
            llm_client=llm_client,
            audit_store=audit_store,
            semaphore=semaphore,
            max_retries=max_retries,
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
    prompt_cache_allowed: bool,
    prompt_loader: PromptLoader,
    llm_client: LLMClient,
    audit_store: AuditStore | None,
    semaphore: asyncio.Semaphore,
    max_retries: int,
) -> ExecutorTaskResult:
    category_fields = _approved_category_fields(plan)
    async with semaphore:
        stage = cast(LLMStage, f"executor.{lens}")
        stage_input = ExecutorStageInput(
            schema_card=schema_card_from_plan(plan),
            lens=lens,
            chunk_view=chunk_view_from_chunk(chunk),
        )
        stable_user_prefix, user_content = split_model_json_before_field(
            stage_input,
            "chunk_view",
        )

        def validate_batch(
            output: ExecutorCandidateBatch,
        ) -> Accepted[ExecutorCandidateBatch] | Complaints:
            return _validate_executor_batch(
                output=output,
                lens=lens,
                chunk=chunk,
                category_fields=category_fields,
                plan=plan,
            )

        result = await llm_client.complete_structured_with_retry(
            StructuredLLMRequest(
                run_id=plan.run_id,
                stage=stage,
                prompt=prompt_loader.load(stage),
                user_content=user_content,
                stable_user_prefix=stable_user_prefix,
                prompt_cache_allowed=prompt_cache_allowed,
                tool_name=f"extract_{lens}_candidates",
                tool_description=f"Extract {lens} candidates from one chunk.",
            ),
            output_model=ExecutorCandidateBatch,
            audit_store=audit_store,
            validate=validate_batch,
            merge=_merge_executor_batch,
            max_retries=max_retries,
        )

    accepted: list[LensCandidate] = []
    rejected: list[LensCandidate] = []
    rejections: list[CandidateRejection] = []
    outcomes: list[tuple[LensCandidate, tuple[RejectionReason, ...], int | None]] = []

    payloads = expand_candidate_payloads(
        payloads=result.output.candidates,
        lens=lens,
        chunk=chunk,
        category_fields=category_fields,
    )

    for index, payload in enumerate(payloads):
        original_start_char = payload.start_char
        payload, resolution = prepare_candidate_payload(payload=payload, chunk=chunk)
        candidate = build_candidate(
            plan=plan,
            lens=lens,
            chunk=chunk,
            payload=payload,
            start_char=resolution.start_char,
            source_text=resolution.source_text,
            candidate_index=index,
            executor_call_id=result.call_log.call_id,
        )
        reasons = _candidate_rejection_reasons(
            candidate=candidate,
            chunk=chunk,
            category_fields=category_fields,
        )
        reasons = [*resolution.rejection_reasons, *reasons]

        if audit_store is not None:
            await audit_store.record_lens_candidate(candidate)

        corrected_from = (
            original_start_char
            if resolution.start_char != original_start_char
            else None
        )
        outcomes.append((candidate, tuple(reasons), corrected_from))

        if reasons:
            rejection = CandidateRejection(
                rejection_id=stable_rejection_id(candidate, reasons),
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

    print_executor_outcomes(
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


def _validate_executor_batch(
    *,
    output: ExecutorCandidateBatch,
    lens: LensName,
    chunk: Chunk,
    category_fields: dict[str, frozenset[str]],
    plan: ExtractionPlan,
) -> Accepted[ExecutorCandidateBatch] | Complaints:
    complaints: list[ItemComplaint] = []
    for index, payload in enumerate(output.candidates):
        candidate_payload, resolution = prepare_candidate_payload(
            payload=payload,
            chunk=chunk,
        )
        candidate = build_candidate(
            plan=plan,
            lens=lens,
            chunk=chunk,
            payload=candidate_payload,
            start_char=resolution.start_char,
            source_text=resolution.source_text,
            candidate_index=index,
            executor_call_id="retry-probe",
        )
        reasons: list[RejectionReason] = [
            *resolution.rejection_reasons,
            *_candidate_rejection_reasons(
                candidate=candidate,
                chunk=chunk,
                category_fields=category_fields,
            ),
        ]
        if reasons:
            complaints.append(
                ItemComplaint(
                    identifier=str(index),
                    message=_format_executor_complaint(
                        index=index,
                        lens=lens,
                        chunk=chunk,
                        payload=payload,
                        reasons=reasons,
                    ),
                )
            )
    if complaints:
        return Complaints(complaints=tuple(complaints))
    return Accepted(output=output)


def _merge_executor_batch(
    prior: ExecutorCandidateBatch,
    retry: ExecutorCandidateBatch,
    bad_ids: frozenset[str],
) -> ExecutorCandidateBatch:
    try:
        bad_indices = sorted(int(identifier) for identifier in bad_ids)
    except ValueError as exc:
        raise LLMRetryMergeError(
            f"executor retry ids must be integer indices: {sorted(bad_ids)}"
        ) from exc
    if len(retry.candidates) != len(bad_indices):
        raise LLMRetryMergeError(
            f"executor retry expected {len(bad_indices)} corrections, "
            f"got {len(retry.candidates)}"
        )
    if bad_indices and (bad_indices[0] < 0 or bad_indices[-1] >= len(prior.candidates)):
        raise LLMRetryMergeError(
            f"executor retry index out of range: {bad_indices}"
        )
    merged = list(prior.candidates)
    for slot, fix in zip(bad_indices, retry.candidates):
        merged[slot] = fix
    return ExecutorCandidateBatch(candidates=tuple(merged))


def _format_executor_complaint(
    *,
    index: int,
    lens: LensName,
    chunk: Chunk,
    payload: ExtractedCandidatePayload,
    reasons: list[RejectionReason],
) -> str:
    relative_start = payload.start_char - chunk.start_char
    relative_end = relative_start + payload.source_length
    if (
        0 <= relative_start <= len(chunk.text)
        and 0 <= relative_end <= len(chunk.text)
        and relative_start <= relative_end
    ):
        claimed_source = chunk.text[relative_start:relative_end]
    else:
        claimed_source = "<offsets out of chunk bounds>"
    constraint = "; ".join(reason.message for reason in reasons)
    return (
        f"Item {index} ({lens}/{payload.category}.{payload.field_name}) was rejected.\n"
        f"You returned: value={payload.value!r}, start_char={payload.start_char}, "
        f"source_length={payload.source_length}, "
        f"chunk_text[start_char-chunk.start_char : ...+source_length]={claimed_source!r}.\n"
        f"Constraint violated: {constraint}.\n"
        f"Action: re-emit ONLY this item with corrected start_char and source_length "
        f"so that chunk.text[start_char - chunk.start_char : "
        f"start_char - chunk.start_char + source_length] is a span that supports the "
        f"emitted value exactly."
    )


def _candidate_rejection_reasons(
    *,
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

    if not _span_matches_chunk(candidate.source_span, chunk):
        reasons.append(
            RejectionReason(
                code="invented_span",
                message="Candidate source span does not match the chunk text at the provided offsets.",
            )
        )
    return reasons


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


__all__ = ["ExecutorError", "execute_plan"]
