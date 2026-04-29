from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from extractor.audit import AuditStore
from extractor.chunker import chunk_document
from extractor.config import ExtractorConfig, RunContext, bind_run_context
from extractor.contracts import RunManifest
from extractor.critic import review_candidates
from extractor.executor import execute_plan
from extractor.ingestion import ingest_document
from extractor.llm import LLMClient, PromptLoader
from extractor.orchestrator.models import PipelineRunResult
from extractor.planner import create_extraction_plan
from extractor.reconciler import reconcile_candidates
from extractor.reporter import write_report
from extractor.verifier import verify_candidates


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
) -> PipelineRunResult:
    actual_run_id = run_id or f"run-{uuid.uuid4().hex}"
    prompt_loader = PromptLoader(config.prompts.directory)
    actual_llm_client = llm_client or LLMClient(config.llm)

    async with AuditStore(config.audit.database_path) as audit_store:
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

        context = RunContext(
            run_id=actual_run_id,
            doc_id=document.doc_id,
            audit_db_path=str(config.audit.database_path),
        )
        try:
            with bind_run_context(context):
                _print_stage("chunker", f"window={config.chunking.window_tokens}t overlap={config.chunking.overlap_tokens}t")
                chunks = await chunk_document(
                    document,
                    config.chunking,
                    audit_store=audit_store,
                )
                _print_stage("chunker.done", f"chunks={len(chunks)}")

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

                _print_stage("executor", f"lenses={list(plan.enabled_lenses)} chunks={len(chunks)}")
                execution = await execute_plan(
                    plan=plan,
                    chunks=chunks,
                    prompt_loader=prompt_loader,
                    llm_client=actual_llm_client,
                    execution_config=config.execution,
                    audit_store=audit_store,
                )
                _print_stage("executor.done", f"candidates={len(execution.accepted_candidates)}")

                _print_stage("critic", f"candidates_in={len(execution.accepted_candidates)}")
                critic = await review_candidates(
                    plan=plan,
                    chunks=chunks,
                    candidates=execution.accepted_candidates,
                    prompt_loader=prompt_loader,
                    llm_client=actual_llm_client,
                    execution_config=config.execution,
                    audit_store=audit_store,
                )
                _print_stage("critic.done", f"accepted={len(critic.accepted_candidates)}")

                _print_stage("verifier", f"candidates_in={len(critic.accepted_candidates)}")
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

                _print_stage("reconciler", f"candidates_in={len(verification.accepted_candidates)}")
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
        except Exception:
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
    )


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
