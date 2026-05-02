from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from extractor.audit import AuditStore, CandidateRejection
from extractor.config import ExecutionConfig
from extractor.contracts import (
    Chunk,
    CriticReport,
    ExtractionPlan,
    LensCandidate,
    RejectionReason,
)
from extractor.llm import (
    Accepted,
    Complaints,
    LLMClient,
    PromptLoader,
    StructuredLLMRequest,
)
from extractor.llm.payloads import split_model_json_before_field
from extractor.llm.views import (
    build_candidate_view_map,
    chunk_view_from_chunk,
    schema_card_from_plan,
    short_candidate_id,
)
from extractor.critic.batching import (
    merge_critic_batch,
    partition_into_batches,
    validate_critic_batch,
)
from extractor.critic.errors import CriticError
from extractor.critic.ids import stable_missing_rejection_id, stable_rejection_id
from extractor.critic.mirroring import mirror_merged_critic_reports
from extractor.critic.models import (
    CriticBatchStageInput,
    CriticBatchVerdicts,
    CriticResult,
    CriticTaskResult,
    CriticVerdict,
)
from extractor.critic.reports import build_report, critic_rejection_reasons
from extractor.critic.validation import validate_critic_inputs


async def review_candidates(
    *,
    plan: ExtractionPlan,
    chunks: tuple[Chunk, ...],
    candidates: tuple[LensCandidate, ...],
    merged_into: dict[str, str] | None = None,
    merged_candidates: tuple[LensCandidate, ...] = (),
    prompt_loader: PromptLoader,
    llm_client: LLMClient,
    execution_config: ExecutionConfig,
    audit_store: AuditStore | None = None,
) -> CriticResult:
    if not candidates:
        return CriticResult(
            accepted_candidates=(),
            rejected_candidates=(),
            reports=(),
            rejections=(),
        )

    chunks_by_id = validate_critic_inputs(plan, chunks, candidates)
    semaphore = asyncio.Semaphore(execution_config.max_stage_concurrency)
    batches = partition_into_batches(candidates, execution_config.critic_batch_size)
    max_retries = max(execution_config.max_llm_attempts - 1, 0)
    cache_primed = (
        asyncio.Event()
        if len(batches) > 1
        and llm_client.config.provider == "anthropic"
        and llm_client.config.prompt_cache_enabled
        else None
    )
    tasks = [
        _review_batch(
            plan=plan,
            chunk=chunks_by_id[batch[0].chunk_id],
            batch=batch,
            batch_index=batch_index,
            cache_primed=cache_primed,
            prompt_loader=prompt_loader,
            llm_client=llm_client,
            audit_store=audit_store,
            semaphore=semaphore,
            max_retries=max_retries,
        )
        for batch_index, batch in enumerate(batches)
    ]
    results = await asyncio.gather(*tasks)
    accepted_candidates = tuple(
        candidate for result in results for candidate in result.accepted_candidates
    )
    rejected_candidates = tuple(
        candidate for result in results for candidate in result.rejected_candidates
    )
    reports = tuple(report for result in results for report in result.reports)
    rejections = tuple(rejection for result in results for rejection in result.rejections)

    (
        mirrored_accepted,
        mirrored_rejected,
        mirrored_reports,
    ) = await mirror_merged_critic_reports(
        plan=plan,
        reports=reports,
        merged_into=merged_into or {},
        merged_candidates=merged_candidates,
        audit_store=audit_store,
    )

    return CriticResult(
        accepted_candidates=(*accepted_candidates, *mirrored_accepted),
        rejected_candidates=(*rejected_candidates, *mirrored_rejected),
        reports=(*reports, *mirrored_reports),
        rejections=rejections,
    )


async def _review_batch(
    *,
    plan: ExtractionPlan,
    chunk: Chunk,
    batch: tuple[LensCandidate, ...],
    batch_index: int,
    cache_primed: asyncio.Event | None,
    prompt_loader: PromptLoader,
    llm_client: LLMClient,
    audit_store: AuditStore | None,
    semaphore: asyncio.Semaphore,
    max_retries: int,
) -> CriticTaskResult:
    if batch_index > 0 and cache_primed is not None:
        await cache_primed.wait()

    candidate_views, candidates_by_view_id = build_candidate_view_map(batch)
    expected_ids = tuple(candidates_by_view_id)
    stage_input = CriticBatchStageInput(
        schema_card=schema_card_from_plan(plan),
        chunk_view=chunk_view_from_chunk(chunk),
        candidates=candidate_views,
    )
    stable_user_prefix, user_content = split_model_json_before_field(
        stage_input,
        "candidates",
    )

    def validate_batch(
        output: CriticBatchVerdicts,
    ) -> Accepted[CriticBatchVerdicts] | Complaints:
        return validate_critic_batch(
            output=output,
            plan=plan,
            chunk=chunk,
            candidates_by_view_id=candidates_by_view_id,
        )

    def merge_batch(
        prior: CriticBatchVerdicts,
        retry: CriticBatchVerdicts,
        bad_ids: frozenset[str],
    ) -> CriticBatchVerdicts:
        return merge_critic_batch(
            prior=prior,
            retry=retry,
            bad_ids=bad_ids,
            expected_ids=expected_ids,
        )

    try:
        async with semaphore:
            result = await llm_client.complete_structured_with_retry(
                StructuredLLMRequest(
                    run_id=plan.run_id,
                    stage="critic",
                    prompt=prompt_loader.load("critic"),
                    user_content=user_content,
                    stable_user_prefix=stable_user_prefix,
                    tool_name="review_candidates_batch",
                    tool_description=(
                        "Review a batch of executor candidates from one chunk for "
                        "plausibility and corrections."
                    ),
                ),
                output_model=CriticBatchVerdicts,
                audit_store=audit_store,
                validate=validate_batch,
                merge=merge_batch,
                max_retries=max_retries,
            )
    finally:
        if batch_index == 0 and cache_primed is not None:
            cache_primed.set()

    verdicts_by_candidate: dict[str, CriticVerdict] = {}
    for verdict in result.output.verdicts:
        # First report wins — the model occasionally repeats an id.
        verdicts_by_candidate.setdefault(verdict.id, verdict)

    accepted_candidates: list[LensCandidate] = []
    rejected_candidates: list[LensCandidate] = []
    reports: list[CriticReport] = []
    rejections: list[CandidateRejection] = []

    for candidate in batch:
        view_id = short_candidate_id(candidate.candidate_id)
        verdict = verdicts_by_candidate.get(view_id)
        if verdict is None:
            reasons = [
                RejectionReason(
                    code="critic_missing_report",
                    message=(
                        "Critic batch response did not include a report for "
                        f"candidate {candidate.candidate_id}."
                    ),
                )
            ]
            rejection = CandidateRejection(
                rejection_id=stable_missing_rejection_id(
                    candidate=candidate,
                    critic_call_id=result.call_log.call_id,
                    reasons=reasons,
                ),
                run_id=plan.run_id,
                candidate_id=candidate.candidate_id,
                stage="critic",
                reasons=tuple(reasons),
                created_at=datetime.now(timezone.utc),
            )
            if audit_store is not None:
                await audit_store.record_candidate_rejection(rejection)
            rejected_candidates.append(candidate)
            rejections.append(rejection)
            continue

        report, corrected_candidate, validation_reasons = build_report(
            plan=plan,
            chunk=chunk,
            candidate=candidate,
            verdict=verdict,
            critic_call_id=result.call_log.call_id,
        )
        if audit_store is not None:
            await audit_store.record_critic_report(report)

        if report.accepted:
            accepted_candidates.append(corrected_candidate or candidate)
            reports.append(report)
            continue

        reasons = validation_reasons or critic_rejection_reasons(report)
        rejection = CandidateRejection(
            rejection_id=stable_rejection_id(candidate, report, reasons),
            run_id=plan.run_id,
            candidate_id=candidate.candidate_id,
            stage="critic",
            reasons=tuple(reasons),
            created_at=datetime.now(timezone.utc),
        )
        if audit_store is not None:
            await audit_store.record_candidate_rejection(rejection)
        rejected_candidates.append(candidate)
        reports.append(report)
        rejections.append(rejection)

    return CriticTaskResult(
        accepted_candidates=tuple(accepted_candidates),
        rejected_candidates=tuple(rejected_candidates),
        reports=tuple(reports),
        rejections=tuple(rejections),
    )


__all__ = ["CriticError", "review_candidates"]
