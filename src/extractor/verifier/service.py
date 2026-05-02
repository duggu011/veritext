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
    VerifierReport,
)
from extractor.llm import LLMClient, PromptLoader, StructuredLLMRequest
from extractor.llm.payloads import split_model_json_before_field
from extractor.llm.views import (
    build_candidate_view_map,
    chunk_view_from_chunk,
    schema_card_from_plan,
    short_candidate_id,
)
from extractor.verifier.errors import VerifierError
from extractor.verifier.models import (
    CriticSummary,
    VerificationResult,
    VerifierBatchItem,
    VerifierBatchVerdicts,
    VerifierBatchStageInput,
    VerifierTaskResult,
    VerifierVerdict,
)
from extractor.verifier.policies import (
    build_verifier_report,
    stable_missing_report_id,
    stable_rejection_id,
)
from extractor.verifier.validation import validate_verifier_inputs


async def verify_candidates(
    *,
    plan: ExtractionPlan,
    chunks: tuple[Chunk, ...],
    candidates: tuple[LensCandidate, ...],
    critic_reports: tuple[CriticReport, ...],
    prompt_loader: PromptLoader,
    llm_client: LLMClient,
    execution_config: ExecutionConfig,
    audit_store: AuditStore | None = None,
) -> VerificationResult:
    if not candidates:
        return VerificationResult(
            accepted_candidates=(),
            rejected_candidates=(),
            reports=(),
            rejections=(),
        )

    chunks_by_id, reports_by_candidate_id = validate_verifier_inputs(
        plan=plan,
        chunks=chunks,
        candidates=candidates,
        critic_reports=critic_reports,
    )
    semaphore = asyncio.Semaphore(execution_config.max_stage_concurrency)
    batches = _partition_into_batches(candidates, execution_config.verifier_batch_size)
    cache_primed = (
        asyncio.Event()
        if len(batches) > 1
        and llm_client.config.provider == "anthropic"
        and llm_client.config.prompt_cache_enabled
        else None
    )
    tasks = [
        _verify_batch(
            plan=plan,
            chunk=chunks_by_id[batch[0].chunk_id],
            batch=batch,
            critic_reports_by_candidate=reports_by_candidate_id,
            batch_index=batch_index,
            cache_primed=cache_primed,
            prompt_loader=prompt_loader,
            llm_client=llm_client,
            audit_store=audit_store,
            semaphore=semaphore,
        )
        for batch_index, batch in enumerate(batches)
    ]
    results = await asyncio.gather(*tasks)

    return VerificationResult(
        accepted_candidates=tuple(
            candidate for result in results for candidate in result.accepted_candidates
        ),
        rejected_candidates=tuple(
            candidate for result in results for candidate in result.rejected_candidates
        ),
        reports=tuple(report for result in results for report in result.reports),
        rejections=tuple(rejection for result in results for rejection in result.rejections),
    )


def _partition_into_batches(
    candidates: tuple[LensCandidate, ...],
    batch_size: int,
) -> list[tuple[LensCandidate, ...]]:
    by_chunk: dict[str, list[LensCandidate]] = {}
    for candidate in candidates:
        by_chunk.setdefault(candidate.chunk_id, []).append(candidate)
    batches: list[tuple[LensCandidate, ...]] = []
    for group in by_chunk.values():
        for start in range(0, len(group), batch_size):
            batches.append(tuple(group[start : start + batch_size]))
    return batches


async def _verify_batch(
    *,
    plan: ExtractionPlan,
    chunk: Chunk,
    batch: tuple[LensCandidate, ...],
    critic_reports_by_candidate: dict[str, CriticReport],
    batch_index: int,
    cache_primed: asyncio.Event | None,
    prompt_loader: PromptLoader,
    llm_client: LLMClient,
    audit_store: AuditStore | None,
    semaphore: asyncio.Semaphore,
) -> VerifierTaskResult:
    candidate_views, _candidates_by_view_id = build_candidate_view_map(batch)
    items = tuple(
        VerifierBatchItem(
            candidate=candidate_view,
            critic_summary=CriticSummary(
                accepted=critic_reports_by_candidate[candidate.candidate_id].accepted
            ),
        )
        for candidate, candidate_view in zip(batch, candidate_views, strict=True)
    )
    if batch_index > 0 and cache_primed is not None:
        await cache_primed.wait()

    stage_input = VerifierBatchStageInput(
        schema_card=schema_card_from_plan(plan),
        chunk_view=chunk_view_from_chunk(chunk),
        items=items,
    )
    stable_user_prefix, user_content = split_model_json_before_field(
        stage_input,
        "items",
    )
    try:
        async with semaphore:
            result = await llm_client.complete_structured(
                StructuredLLMRequest(
                    run_id=plan.run_id,
                    stage="verifier",
                    prompt=prompt_loader.load("verifier"),
                    user_content=user_content,
                    stable_user_prefix=stable_user_prefix,
                    tool_name="verify_candidates_batch",
                    tool_description=(
                        "Verify a batch of critic-accepted candidates from one chunk "
                        "against source and schema."
                    ),
                ),
                output_model=VerifierBatchVerdicts,
                audit_store=audit_store,
            )
    finally:
        if batch_index == 0 and cache_primed is not None:
            cache_primed.set()

    verdicts_by_candidate: dict[str, VerifierVerdict] = {}
    for verdict in result.output.verdicts:
        verdicts_by_candidate.setdefault(verdict.id, verdict)

    accepted_candidates: list[LensCandidate] = []
    rejected_candidates: list[LensCandidate] = []
    reports: list[VerifierReport] = []
    rejections: list[CandidateRejection] = []

    for candidate in batch:
        view_id = short_candidate_id(candidate.candidate_id)
        verdict = verdicts_by_candidate.get(view_id)
        if verdict is None:
            reasons = (
                RejectionReason(
                    code="verifier_missing_report",
                    message=(
                        "Verifier batch response did not include a report for "
                        f"candidate {candidate.candidate_id}."
                    ),
                ),
            )
            report = VerifierReport(
                report_id=stable_missing_report_id(
                    candidate=candidate,
                    verifier_call_id=result.call_log.call_id,
                    reasons=reasons,
                ),
                run_id=plan.run_id,
                candidate_id=candidate.candidate_id,
                verifier_call_id=result.call_log.call_id,
                span_verified=False,
                category_verified=False,
                alignment_score=0.0,
                accepted=False,
                rejection_reasons=reasons,
            )
            if audit_store is not None:
                await audit_store.record_verifier_report(report)
            rejection = CandidateRejection(
                rejection_id=stable_rejection_id(candidate, report),
                run_id=plan.run_id,
                candidate_id=candidate.candidate_id,
                stage="verifier",
                reasons=reasons,
                created_at=datetime.now(timezone.utc),
            )
            if audit_store is not None:
                await audit_store.record_candidate_rejection(rejection)
            rejected_candidates.append(candidate)
            reports.append(report)
            rejections.append(rejection)
            continue

        report = build_verifier_report(
            plan=plan,
            chunk=chunk,
            candidate=candidate,
            verdict=verdict,
            verifier_call_id=result.call_log.call_id,
        )
        if audit_store is not None:
            await audit_store.record_verifier_report(report)

        if report.accepted:
            accepted_candidates.append(candidate)
            reports.append(report)
            continue

        rejection = CandidateRejection(
            rejection_id=stable_rejection_id(candidate, report),
            run_id=plan.run_id,
            candidate_id=candidate.candidate_id,
            stage="verifier",
            reasons=report.rejection_reasons,
            created_at=datetime.now(timezone.utc),
        )
        if audit_store is not None:
            await audit_store.record_candidate_rejection(rejection)
        rejected_candidates.append(candidate)
        reports.append(report)
        rejections.append(rejection)

    return VerifierTaskResult(
        accepted_candidates=tuple(accepted_candidates),
        rejected_candidates=tuple(rejected_candidates),
        reports=tuple(reports),
        rejections=tuple(rejections),
    )


__all__ = ["VerifierError", "verify_candidates"]
