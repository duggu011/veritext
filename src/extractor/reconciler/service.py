from __future__ import annotations

from extractor.audit import AuditStore
from extractor.contracts import (
    CriticReport,
    ExtractionPlan,
    LensCandidate,
    VerifierReport,
)
from extractor.llm import (
    LLMClient,
    PromptLoader,
    StructuredLLMRequest,
)
from extractor.llm.views import build_candidate_view_map, schema_card_from_plan
from extractor.reconciler.batching import (
    expand_reconciliation_batch_ids as _expand_reconciliation_batch_ids,
    replace_reconciliation_batch as _replace_reconciliation_batch,
    validate_reconciliation_batch as _validate_reconciliation_batch,
)
from extractor.reconciler.errors import ReconcilerError
from extractor.reconciler.materialization import (
    build_reconciliation_result as _build_reconciliation_result,
)
from extractor.reconciler.models import (
    ReconciliationBatch,
    ReconciliationResult,
    ReconcilerStageInput,
)
from extractor.reconciler.validation import (
    validate_reconciler_inputs as _validate_reconciler_inputs,
)


async def reconcile_candidates(
    *,
    plan: ExtractionPlan,
    candidates: tuple[LensCandidate, ...],
    critic_reports: tuple[CriticReport, ...],
    verifier_reports: tuple[VerifierReport, ...],
    prompt_loader: PromptLoader,
    llm_client: LLMClient,
    audit_store: AuditStore | None = None,
    max_retries: int = 1,
) -> ReconciliationResult:
    if not candidates:
        return ReconciliationResult(data_points=(), rejections=())

    critic_reports_by_candidate_id, verifier_reports_by_candidate_id = _validate_reconciler_inputs(
        plan=plan,
        candidates=candidates,
        critic_reports=critic_reports,
        verifier_reports=verifier_reports,
    )
    try:
        candidate_views, candidates_by_view_id = build_candidate_view_map(candidates)
    except ValueError as exc:
        raise ReconcilerError(str(exc)) from exc

    request = StructuredLLMRequest(
        run_id=plan.run_id,
        stage="reconciler",
        prompt=prompt_loader.load("reconciler"),
        user_content=ReconcilerStageInput(
            schema_card=schema_card_from_plan(plan),
            candidates=candidate_views,
        ).model_dump_json(),
        tool_name="reconcile_candidates",
        tool_description="Reconcile verified candidates into final source-backed data points.",
    )
    if max_retries > 0 and llm_client.config.provider == "anthropic":
        result = await llm_client.complete_structured_with_retry(
            request,
            output_model=ReconciliationBatch,
            audit_store=audit_store,
            validate=lambda batch: _validate_reconciliation_batch(
                batch=batch,
                candidates_by_view_id=candidates_by_view_id,
            ),
            merge=_replace_reconciliation_batch,
            max_retries=max_retries,
        )
    else:
        result = await llm_client.complete_structured(
            request,
            output_model=ReconciliationBatch,
            audit_store=audit_store,
        )
    expanded_batch = _expand_reconciliation_batch_ids(
        batch=result.output,
        candidates_by_view_id=candidates_by_view_id,
    )

    data_points, rejections = _build_reconciliation_result(
        plan=plan,
        candidates_by_id={candidate.candidate_id: candidate for candidate in candidates},
        critic_reports_by_candidate_id=critic_reports_by_candidate_id,
        verifier_reports_by_candidate_id=verifier_reports_by_candidate_id,
        batch=expanded_batch,
    )
    if audit_store is not None:
        for data_point in data_points:
            await audit_store.record_data_point(data_point)
        for rejection in rejections:
            await audit_store.record_candidate_rejection(rejection)
    return ReconciliationResult(data_points=data_points, rejections=rejections)


__all__ = ["ReconcilerError", "reconcile_candidates"]
