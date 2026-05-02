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
)
from extractor.contracts.models import LLMStage, LensName
from extractor.llm import (
    LLMClient,
    PromptLoader,
    StructuredLLMRequest,
)
from extractor.llm.payloads import split_model_json_before_field
from extractor.llm.views import chunk_view_from_chunk, schema_card_from_plan
from extractor.executor.errors import ExecutorError
from extractor.executor.batching import merge_executor_batch, validate_executor_batch
from extractor.executor.ids import stable_rejection_id
from extractor.executor.materialization import build_candidate
from extractor.executor.models import (
    ExecutionResult,
    ExecutorCandidateBatch,
    ExecutorStageInput,
    ExecutorTaskResult,
)
from extractor.executor.normalization import prepare_candidate_payload
from extractor.executor.payload_expansion import expand_candidate_payloads
from extractor.executor.policies import (
    approved_category_fields,
    candidate_rejection_reasons,
)
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
    category_fields = approved_category_fields(plan)
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
        ):
            return validate_executor_batch(
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
            merge=merge_executor_batch,
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
        reasons = candidate_rejection_reasons(
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


__all__ = ["ExecutorError", "execute_plan"]
