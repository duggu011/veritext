from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from extractor.audit import (
    AuditStore,
    CandidateRejection,
    RunStageName,
    RunStageState,
)
from extractor.chunker import chunk_document
from extractor.config import ChunkingConfig, ExtractorConfig, RunContext, bind_run_context
from extractor.contracts import (
    Chunk,
    CriticReport,
    DataPoint,
    Document,
    ExtractionPlan,
    LensCandidate,
    RunManifest,
    VerifierReport,
)
from extractor.critic import CriticResult, review_candidates
from extractor.executor import (
    ExecutionResult,
    build_dedup_rejections,
    deduplicate_candidates,
    execute_plan,
)
from extractor.ingestion import ingest_document
from extractor.llm import LLMClient, PromptLoader
from extractor.orchestrator.models import PipelineRunResult
from extractor.planner import create_extraction_plan
from extractor.reconciler import ReconciliationResult, reconcile_candidates
from extractor.reporter import write_report
from extractor.verifier import VerificationResult, verify_candidates


class OrchestratorError(RuntimeError):
    """Raised when a full extraction run cannot be orchestrated safely."""


_STAGE_BANNER = "#" * 100


def _stage_trace_enabled() -> bool:
    # Mirrors the LLM trace toggle so a single env switch silences both.
    return os.environ.get("EXTRACTOR_LLM_TRACE", "1") not in {"0", "false", "False", ""}


def _print_stage(name: str, detail: str = "") -> None:
    if not _stage_trace_enabled():
        return
    suffix = f"  | {detail}" if detail else ""
    print(
        f"\n{_STAGE_BANNER}\n  -> {name.upper()}{suffix}\n{_STAGE_BANNER}",
        file=sys.stderr,
        flush=True,
    )


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

    actual_run_id = run_id or f"run-{uuid.uuid4().hex}"
    prompt_loader = PromptLoader(config.prompts.directory)
    actual_llm_client = llm_client or LLMClient(config.llm)

    async with AuditStore(config.audit.database_path) as audit_store:
        existing_manifest = await audit_store.get_run_manifest(actual_run_id)
        if existing_manifest is not None and not resume:
            raise OrchestratorError(
                "Run ID already exists in the audit database: "
                f"{actual_run_id}. Use --resume to continue that run, or choose "
                "a new --run-id."
            )
        if existing_manifest is None and resume:
            raise OrchestratorError(
                f"Cannot resume run_id {actual_run_id!r}: no run manifest exists."
            )
        if existing_manifest is not None and existing_manifest.status == "completed":
            raise OrchestratorError(
                f"Cannot resume run_id {actual_run_id!r}: the run is already completed."
            )

        running_manifest: RunManifest | None = None
        try:
            if existing_manifest is None:
                _print_stage("ingestion", f"source={source_path} run_id={actual_run_id}")
                document = await ingest_document(source_path, audit_store=audit_store)
                _print_stage(
                    "ingestion.done",
                    f"doc_id={document.doc_id} bytes={document.text_byte_length}",
                )
                started_at = datetime.now(timezone.utc)
                created_manifest = RunManifest(
                    run_id=actual_run_id,
                    doc_id=document.doc_id,
                    audit_db_path=str(config.audit.database_path),
                    status="created",
                    started_at=started_at,
                    output_data_point_ids=(),
                )
                await audit_store.record_run_manifest(created_manifest)
                running_manifest = _transition_manifest(created_manifest, status="running")
                await audit_store.update_run_manifest(running_manifest)
                await _ensure_stage_completed(
                    audit_store,
                    run_id=actual_run_id,
                    stage="ingestion",
                )
            else:
                _print_stage("resume", f"source={source_path} run_id={actual_run_id}")
                document = await _load_resume_document(
                    source_path=source_path,
                    manifest=existing_manifest,
                    audit_store=audit_store,
                )
                _print_stage(
                    "resume.done",
                    f"doc_id={document.doc_id} status={existing_manifest.status}",
                )
                running_manifest = _transition_manifest(existing_manifest, status="running")
                await audit_store.update_run_manifest(running_manifest)
                await _ensure_stage_completed(
                    audit_store,
                    run_id=actual_run_id,
                    stage="ingestion",
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
                failed_manifest = _transition_manifest(
                    running_manifest,
                    status="failed",
                    completed_at=datetime.now(timezone.utc),
                )
                await audit_store.update_run_manifest(failed_manifest)
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


async def _load_resume_document(
    *,
    source_path: str | Path,
    manifest: RunManifest,
    audit_store: AuditStore,
) -> Document:
    document = await ingest_document(source_path, audit_store=None)
    if document.doc_id != manifest.doc_id:
        raise OrchestratorError(
            "Cannot resume: source document does not match the existing run "
            f"manifest doc_id {manifest.doc_id}."
        )

    stored_document = await audit_store.get_document(manifest.doc_id)
    if stored_document is None:
        await audit_store.record_document(document)
        return document
    if stored_document != document:
        raise OrchestratorError(
            "Cannot resume: source document payload differs from the audited "
            f"document {manifest.doc_id}."
        )
    return stored_document


def _validate_resume_chunks(
    *,
    document: Document,
    chunks: tuple[Chunk, ...],
) -> tuple[Chunk, ...]:
    if not chunks:
        raise OrchestratorError("Cannot resume: audited chunk list is empty.")
    expected_indexes = tuple(range(len(chunks)))
    actual_indexes = tuple(chunk.chunk_index for chunk in chunks)
    if actual_indexes != expected_indexes:
        raise OrchestratorError("Cannot resume: audited chunk indexes are not contiguous.")
    for chunk in chunks:
        if chunk.doc_id != document.doc_id:
            raise OrchestratorError("Cannot resume: chunk doc_id does not match document.")
        if document.text[chunk.start_char : chunk.end_char] != chunk.text:
            raise OrchestratorError("Cannot resume: chunk text no longer matches document offsets.")
    return chunks


def _validate_resume_plan(
    *,
    plan: ExtractionPlan,
    document: Document,
    chunking_config: ChunkingConfig,
) -> ExtractionPlan:
    if plan.doc_id != document.doc_id:
        raise OrchestratorError("Cannot resume: extraction plan doc_id does not match document.")
    if plan.chunk_policy.window_tokens != chunking_config.window_tokens:
        raise OrchestratorError("Cannot resume: configured chunk window changed since planning.")
    if plan.chunk_policy.overlap_tokens != chunking_config.overlap_tokens:
        raise OrchestratorError("Cannot resume: configured chunk overlap changed since planning.")
    return plan


async def _ensure_stage_completed(
    audit_store: AuditStore,
    *,
    run_id: str,
    stage: RunStageName,
) -> None:
    if await audit_store.get_run_stage_state(run_id, stage) is not None:
        return
    await audit_store.record_run_stage_state(
        RunStageState(
            run_id=run_id,
            stage=stage,
            completed_at=datetime.now(timezone.utc),
        )
    )


def _execution_result_from_audit(
    *,
    plan: ExtractionPlan,
    candidates: tuple[LensCandidate, ...],
    rejections: tuple[CandidateRejection, ...],
) -> ExecutionResult:
    for candidate in candidates:
        if candidate.run_id != plan.run_id:
            raise OrchestratorError("Cannot resume: candidate run_id does not match plan.")
        if candidate.doc_id != plan.doc_id:
            raise OrchestratorError("Cannot resume: candidate doc_id does not match plan.")

    executor_rejections = tuple(
        rejection for rejection in rejections if rejection.stage == "executor"
    )
    rejected_candidate_ids = {rejection.candidate_id for rejection in executor_rejections}
    candidates_by_id = _candidate_map(candidates)
    rejected_candidates = tuple(
        candidates_by_id[candidate_id]
        for candidate_id in sorted(rejected_candidate_ids)
        if candidate_id in candidates_by_id
    )
    accepted_candidates = tuple(
        candidate
        for candidate in candidates
        if candidate.candidate_id not in rejected_candidate_ids
    )
    return ExecutionResult(
        accepted_candidates=accepted_candidates,
        rejected_candidates=rejected_candidates,
        rejections=executor_rejections,
    )


def _critic_complete(
    *,
    candidates: tuple[LensCandidate, ...],
    reports: tuple[CriticReport, ...],
    rejections: tuple[CandidateRejection, ...],
) -> bool:
    return _review_stage_complete(
        stage="critic",
        candidate_ids=tuple(candidate.candidate_id for candidate in candidates),
        report_candidate_ids=tuple(report.candidate_id for report in reports),
        rejections=rejections,
    )


def _critic_result_from_audit(
    *,
    candidates: tuple[LensCandidate, ...],
    reports: tuple[CriticReport, ...],
    rejections: tuple[CandidateRejection, ...],
) -> CriticResult:
    candidates_by_id = _candidate_map(candidates)
    critic_rejections = tuple(
        rejection for rejection in rejections if rejection.stage == "critic"
    )
    accepted: list[LensCandidate] = []
    rejected_by_id: dict[str, LensCandidate] = {}
    reported_ids: set[str] = set()
    for report in reports:
        candidate = candidates_by_id.get(report.candidate_id)
        if candidate is None:
            raise OrchestratorError(
                f"Cannot resume: critic report references missing candidate {report.candidate_id}."
            )
        reported_ids.add(report.candidate_id)
        if report.accepted:
            accepted.append(report.corrected_candidate or candidate)
        else:
            rejected_by_id[report.candidate_id] = candidate

    for rejection in critic_rejections:
        candidate = candidates_by_id.get(rejection.candidate_id)
        if candidate is None:
            raise OrchestratorError(
                "Cannot resume: critic rejection references missing candidate "
                f"{rejection.candidate_id}."
            )
        if rejection.candidate_id not in reported_ids:
            rejected_by_id[rejection.candidate_id] = candidate

    return CriticResult(
        accepted_candidates=tuple(accepted),
        rejected_candidates=tuple(rejected_by_id[candidate_id] for candidate_id in sorted(rejected_by_id)),
        reports=reports,
        rejections=critic_rejections,
    )


def _verifier_complete(
    *,
    candidates: tuple[LensCandidate, ...],
    reports: tuple[VerifierReport, ...],
    rejections: tuple[CandidateRejection, ...],
) -> bool:
    return _review_stage_complete(
        stage="verifier",
        candidate_ids=tuple(candidate.candidate_id for candidate in candidates),
        report_candidate_ids=tuple(report.candidate_id for report in reports),
        rejections=rejections,
    )


def _verification_result_from_audit(
    *,
    candidates: tuple[LensCandidate, ...],
    reports: tuple[VerifierReport, ...],
    rejections: tuple[CandidateRejection, ...],
) -> VerificationResult:
    candidates_by_id = _candidate_map(candidates)
    verifier_rejections = tuple(
        rejection for rejection in rejections if rejection.stage == "verifier"
    )
    accepted: list[LensCandidate] = []
    rejected_by_id: dict[str, LensCandidate] = {}
    reported_ids: set[str] = set()
    for report in reports:
        candidate = candidates_by_id.get(report.candidate_id)
        if candidate is None:
            raise OrchestratorError(
                "Cannot resume: verifier report references missing candidate "
                f"{report.candidate_id}."
            )
        reported_ids.add(report.candidate_id)
        if report.accepted:
            accepted.append(candidate)
        else:
            rejected_by_id[report.candidate_id] = candidate

    for rejection in verifier_rejections:
        candidate = candidates_by_id.get(rejection.candidate_id)
        if candidate is None:
            raise OrchestratorError(
                "Cannot resume: verifier rejection references missing candidate "
                f"{rejection.candidate_id}."
            )
        if rejection.candidate_id not in reported_ids:
            rejected_by_id[rejection.candidate_id] = candidate

    return VerificationResult(
        accepted_candidates=tuple(accepted),
        rejected_candidates=tuple(rejected_by_id[candidate_id] for candidate_id in sorted(rejected_by_id)),
        reports=reports,
        rejections=verifier_rejections,
    )


def _review_stage_complete(
    *,
    stage: str,
    candidate_ids: tuple[str, ...],
    report_candidate_ids: tuple[str, ...],
    rejections: tuple[CandidateRejection, ...],
) -> bool:
    if not candidate_ids:
        return True
    expected = set(candidate_ids)
    accounted = set(report_candidate_ids)
    accounted.update(
        rejection.candidate_id for rejection in rejections if rejection.stage == stage
    )
    relevant_accounted = expected & accounted
    if not relevant_accounted:
        return False
    missing = expected - accounted
    if missing:
        raise OrchestratorError(
            "Cannot safely resume: audited "
            f"{stage} output is partial for candidates: {', '.join(sorted(missing))}."
        )
    return True


def _reconciler_complete(
    *,
    candidates: tuple[LensCandidate, ...],
    data_points: tuple[DataPoint, ...],
    rejections: tuple[CandidateRejection, ...],
) -> bool:
    if not candidates:
        return True
    expected = {candidate.candidate_id for candidate in candidates}
    reconciler_rejections = tuple(
        rejection for rejection in rejections if rejection.stage == "reconciler"
    )
    if not data_points and not reconciler_rejections:
        return False

    accounted: set[str] = set()
    for data_point in data_points:
        accounted.update(data_point.contributing_candidate_ids)
    accounted.update(rejection.candidate_id for rejection in reconciler_rejections)
    missing = expected - accounted
    if missing:
        raise OrchestratorError(
            "Cannot safely resume: audited reconciler output is partial for "
            f"candidates: {', '.join(sorted(missing))}."
        )
    return True


def _reconciliation_result_from_audit(
    *,
    data_points: tuple[DataPoint, ...],
    rejections: tuple[CandidateRejection, ...],
) -> ReconciliationResult:
    return ReconciliationResult(
        data_points=data_points,
        rejections=tuple(
            rejection for rejection in rejections if rejection.stage == "reconciler"
        ),
    )


def _candidate_map(candidates: tuple[LensCandidate, ...]) -> dict[str, LensCandidate]:
    candidates_by_id: dict[str, LensCandidate] = {}
    for candidate in candidates:
        if candidate.candidate_id in candidates_by_id:
            raise OrchestratorError(
                f"Cannot resume: duplicate candidate ID {candidate.candidate_id}."
            )
        candidates_by_id[candidate.candidate_id] = candidate
    return candidates_by_id


def _transition_manifest(
    manifest: RunManifest,
    *,
    status: str,
    completed_at: datetime | None = None,
) -> RunManifest:
    return RunManifest(
        run_id=manifest.run_id,
        doc_id=manifest.doc_id,
        audit_db_path=manifest.audit_db_path,
        status=status,
        started_at=manifest.started_at,
        completed_at=completed_at,
        output_data_point_ids=manifest.output_data_point_ids,
    )


__all__ = ["OrchestratorError", "run_extraction_pipeline"]
