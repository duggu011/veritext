from __future__ import annotations

import uuid
from pathlib import Path

from extractor.audit import AuditStore
from extractor.chunker import chunk_document
from extractor.config import ExtractorConfig, RunContext, bind_run_context
from extractor.contracts import RunManifest
from extractor.critic import review_candidates
from extractor.executor import (
    ExecutionResult,
    build_dedup_rejections,
    deduplicate_candidates,
    execute_plan,
)
from extractor.llm import LLMClient, PromptLoader
from extractor.orchestrator.errors import OrchestratorError
from extractor.orchestrator.lifecycle import (
    mark_run_failed as _mark_run_failed,
    start_or_resume_run as _start_or_resume_run,
)
from extractor.orchestrator.models import PipelineRunResult
from extractor.orchestrator.state import (
    critic_complete as _critic_complete,
    critic_result_from_audit as _critic_result_from_audit,
    ensure_stage_completed as _ensure_stage_completed,
    execution_result_from_audit as _execution_result_from_audit,
    reconciliation_result_from_audit as _reconciliation_result_from_audit,
    reconciler_complete as _reconciler_complete,
    validate_resume_chunks as _validate_resume_chunks,
    validate_resume_plan as _validate_resume_plan,
    verification_result_from_audit as _verification_result_from_audit,
    verifier_complete as _verifier_complete,
)
from extractor.orchestrator.trace import print_stage as _print_stage
from extractor.planner import (
    DomainPackLoaderError,
    create_extraction_plan,
    load_domain_pack_artifacts,
)
from extractor.reconciler import reconcile_candidates
from extractor.reporter import write_report
from extractor.verifier import verify_candidates


async def run_extraction_pipeline(
    *,
    source_path: str | Path,
    output_path: str | Path,
    config: ExtractorConfig,
    llm_client: LLMClient | None = None,
    run_id: str | None = None,
    domain_hints: tuple[str, ...] = (),
    resume: bool = False,
) -> PipelineRunResult:
    if resume and run_id is None:
        raise OrchestratorError("--resume requires an explicit --run-id")

    try:
        # Phase 26 validates configured pack artifacts but does not use them
        # for planner selection or schema reuse yet.
        load_domain_pack_artifacts(config.domain_packs.directory)
    except DomainPackLoaderError as exc:
        raise OrchestratorError(f"Invalid domain-pack configuration: {exc}") from exc

    actual_run_id = run_id or f"run-{uuid.uuid4().hex}"
    prompt_loader = PromptLoader(config.prompts.directory)
    actual_llm_client = llm_client or LLMClient(config.llm)

    async with AuditStore(config.audit.database_path) as audit_store:
        running_manifest: RunManifest | None = None
        try:
            document, running_manifest = await _start_or_resume_run(
                audit_store=audit_store,
                source_path=source_path,
                audit_db_path=config.audit.database_path,
                run_id=actual_run_id,
                resume=resume,
            )

            context = RunContext(
                run_id=actual_run_id,
                doc_id=document.doc_id,
                audit_db_path=str(config.audit.database_path),
            )
            with bind_run_context(context):
                stored_chunks = await audit_store.list_chunks(document.doc_id)
                chunker_state = await audit_store.get_run_stage_state(
                    actual_run_id,
                    "chunker",
                )
                if stored_chunks:
                    chunks = _validate_resume_chunks(
                        document=document,
                        chunks=stored_chunks,
                    )
                    _print_stage("chunker.resume", f"chunks={len(chunks)}")
                elif chunker_state is not None:
                    raise OrchestratorError(
                        "Cannot resume: chunker is marked complete but no chunks "
                        f"exist for document {document.doc_id}."
                    )
                else:
                    _print_stage(
                        "chunker",
                        (
                            f"window={config.chunking.window_tokens}t "
                            f"overlap={config.chunking.overlap_tokens}t"
                        ),
                    )
                    chunks = await chunk_document(
                        document,
                        config.chunking,
                        audit_store=audit_store,
                    )
                _print_stage("chunker.done", f"chunks={len(chunks)}")
                await _ensure_stage_completed(
                    audit_store,
                    run_id=actual_run_id,
                    stage="chunker",
                )

                stored_plan = await audit_store.get_extraction_plan(actual_run_id)
                planner_state = await audit_store.get_run_stage_state(
                    actual_run_id,
                    "planner",
                )
                if stored_plan is not None:
                    plan = _validate_resume_plan(
                        plan=stored_plan,
                        document=document,
                        chunking_config=config.chunking,
                    )
                    _print_stage("planner.resume", f"lenses={list(plan.enabled_lenses)}")
                elif planner_state is not None:
                    raise OrchestratorError(
                        "Cannot resume: planner is marked complete but no extraction "
                        f"plan exists for run {actual_run_id}."
                    )
                else:
                    _print_stage("planner", f"domain_hints={list(domain_hints) or 'none'}")
                    plan = await create_extraction_plan(
                        run_id=actual_run_id,
                        document=document,
                        chunks=chunks,
                        chunking_config=config.chunking,
                        prompt_loader=prompt_loader,
                        llm_client=actual_llm_client,
                        domain_hints=domain_hints,
                        audit_store=audit_store,
                    )
                _print_stage(
                    "planner.done",
                    f"categories={[c.name for c in plan.approved_categories]} lenses={list(plan.enabled_lenses)}",
                )
                await _ensure_stage_completed(
                    audit_store,
                    run_id=actual_run_id,
                    stage="planner",
                )

                existing_candidates = await audit_store.list_lens_candidates(actual_run_id)
                existing_rejections = await audit_store.list_candidate_rejections_for_run(
                    actual_run_id
                )
                executor_state = await audit_store.get_run_stage_state(
                    actual_run_id,
                    "executor",
                )
                if existing_candidates:
                    execution = _execution_result_from_audit(
                        plan=plan,
                        candidates=existing_candidates,
                        rejections=existing_rejections,
                    )
                    _print_stage(
                        "executor.resume",
                        f"candidates={len(execution.accepted_candidates)}",
                    )
                elif executor_state is not None:
                    execution = ExecutionResult(
                        accepted_candidates=(),
                        rejected_candidates=(),
                        rejections=(),
                    )
                    _print_stage("executor.resume", "candidates=0")
                else:
                    _print_stage(
                        "executor",
                        f"lenses={list(plan.enabled_lenses)} chunks={len(chunks)}",
                    )
                    execution = await execute_plan(
                        plan=plan,
                        chunks=chunks,
                        prompt_loader=prompt_loader,
                        llm_client=actual_llm_client,
                        execution_config=config.execution,
                        audit_store=audit_store,
                    )
                _print_stage("executor.done", f"candidates={len(execution.accepted_candidates)}")
                await _ensure_stage_completed(
                    audit_store,
                    run_id=actual_run_id,
                    stage="executor",
                )

                canonical_candidates, merged_into = deduplicate_candidates(
                    execution.accepted_candidates
                )
                dedup_rejections = build_dedup_rejections(
                    run_id=plan.run_id,
                    candidates=execution.accepted_candidates,
                    merged_into=merged_into,
                )
                existing_rejection_ids = {
                    rejection.rejection_id for rejection in existing_rejections
                }
                for rejection in dedup_rejections:
                    if rejection.rejection_id not in existing_rejection_ids:
                        await audit_store.record_candidate_rejection(rejection)
                merged_candidate_ids = set(merged_into)
                merged_candidates = tuple(
                    candidate
                    for candidate in execution.accepted_candidates
                    if candidate.candidate_id in merged_candidate_ids
                )
                _print_stage(
                    "dedup.done",
                    (
                        f"canonical={len(canonical_candidates)} "
                        f"duplicates={len(merged_into)}"
                    ),
                )
                await _ensure_stage_completed(
                    audit_store,
                    run_id=actual_run_id,
                    stage="dedup",
                )

                critic_reports = await audit_store.list_critic_reports_for_run(actual_run_id)
                all_rejections = await audit_store.list_candidate_rejections_for_run(
                    actual_run_id
                )
                if _critic_complete(
                    candidates=canonical_candidates,
                    reports=critic_reports,
                    rejections=all_rejections,
                ):
                    critic = _critic_result_from_audit(
                        candidates=execution.accepted_candidates,
                        reports=critic_reports,
                        rejections=all_rejections,
                    )
                    _print_stage(
                        "critic.resume",
                        f"accepted={len(critic.accepted_candidates)}",
                    )
                else:
                    _print_stage("critic", f"candidates_in={len(canonical_candidates)}")
                    critic = await review_candidates(
                        plan=plan,
                        chunks=chunks,
                        candidates=canonical_candidates,
                        merged_into=merged_into,
                        merged_candidates=merged_candidates,
                        prompt_loader=prompt_loader,
                        llm_client=actual_llm_client,
                        execution_config=config.execution,
                        audit_store=audit_store,
                    )
                _print_stage("critic.done", f"accepted={len(critic.accepted_candidates)}")
                await _ensure_stage_completed(
                    audit_store,
                    run_id=actual_run_id,
                    stage="critic",
                )

                verifier_reports = await audit_store.list_verifier_reports_for_run(
                    actual_run_id
                )
                all_rejections = await audit_store.list_candidate_rejections_for_run(
                    actual_run_id
                )
                if _verifier_complete(
                    candidates=critic.accepted_candidates,
                    reports=verifier_reports,
                    rejections=all_rejections,
                ):
                    verification = _verification_result_from_audit(
                        candidates=critic.accepted_candidates,
                        reports=verifier_reports,
                        rejections=all_rejections,
                    )
                    _print_stage(
                        "verifier.resume",
                        f"accepted={len(verification.accepted_candidates)}",
                    )
                else:
                    _print_stage(
                        "verifier",
                        f"candidates_in={len(critic.accepted_candidates)}",
                    )
                    verification = await verify_candidates(
                        plan=plan,
                        chunks=chunks,
                        candidates=critic.accepted_candidates,
                        critic_reports=critic.reports,
                        prompt_loader=prompt_loader,
                        llm_client=actual_llm_client,
                        execution_config=config.execution,
                        audit_store=audit_store,
                    )
                _print_stage("verifier.done", f"accepted={len(verification.accepted_candidates)}")
                await _ensure_stage_completed(
                    audit_store,
                    run_id=actual_run_id,
                    stage="verifier",
                )

                data_points = await audit_store.list_data_points(actual_run_id)
                all_rejections = await audit_store.list_candidate_rejections_for_run(
                    actual_run_id
                )
                if _reconciler_complete(
                    candidates=verification.accepted_candidates,
                    data_points=data_points,
                    rejections=all_rejections,
                ):
                    reconciliation = _reconciliation_result_from_audit(
                        data_points=data_points,
                        rejections=all_rejections,
                    )
                    _print_stage(
                        "reconciler.resume",
                        f"data_points={len(reconciliation.data_points)}",
                    )
                else:
                    _print_stage(
                        "reconciler",
                        f"candidates_in={len(verification.accepted_candidates)}",
                    )
                    reconciliation = await reconcile_candidates(
                        plan=plan,
                        candidates=verification.accepted_candidates,
                        critic_reports=critic.reports,
                        verifier_reports=verification.reports,
                        prompt_loader=prompt_loader,
                        llm_client=actual_llm_client,
                        audit_store=audit_store,
                        max_retries=max(config.execution.max_llm_attempts - 1, 0),
                    )
                _print_stage("reconciler.done", f"data_points={len(reconciliation.data_points)}")
                await _ensure_stage_completed(
                    audit_store,
                    run_id=actual_run_id,
                    stage="reconciler",
                )

                _print_stage("reporter", f"output={output_path}")
                report = await write_report(
                    manifest=running_manifest,
                    data_points=reconciliation.data_points,
                    output_path=output_path,
                    audit_store=audit_store,
                )
                _print_stage(
                    "reporter.done",
                    f"output={report.output_path} sha256={report.output_sha256[:12]}…",
                )
                await _ensure_stage_completed(
                    audit_store,
                    run_id=actual_run_id,
                    stage="reporter",
                )
                usage_summary = await audit_store.summarize_run(actual_run_id)
        except Exception:
            if running_manifest is not None:
                await _mark_run_failed(
                    audit_store,
                    running_manifest=running_manifest,
                )
            raise

    return PipelineRunResult(
        run_id=actual_run_id,
        document=document,
        chunks=chunks,
        plan=plan,
        execution=execution,
        critic=critic,
        verification=verification,
        reconciliation=reconciliation,
        report=report,
        completed_manifest=report.completed_manifest,
        usage_summary=usage_summary,
    )


__all__ = ["OrchestratorError", "run_extraction_pipeline"]
