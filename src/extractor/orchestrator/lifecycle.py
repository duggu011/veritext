from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from extractor.audit import AuditStore
from extractor.contracts import Document, RunManifest
from extractor.ingestion import ingest_document
from extractor.orchestrator.errors import OrchestratorError
from extractor.orchestrator.state import (
    ensure_stage_completed,
    load_resume_document,
    transition_manifest,
)
from extractor.orchestrator.trace import print_stage


async def start_or_resume_run(
    *,
    audit_store: AuditStore,
    source_path: str | Path,
    audit_db_path: str | Path,
    run_id: str,
    resume: bool,
) -> tuple[Document, RunManifest]:
    existing_manifest = await audit_store.get_run_manifest(run_id)
    if existing_manifest is not None and not resume:
        raise OrchestratorError(
            "Run ID already exists in the audit database: "
            f"{run_id}. Use --resume to continue that run, or choose a new --run-id."
        )
    if existing_manifest is None and resume:
        raise OrchestratorError(f"Cannot resume run_id {run_id!r}: no run manifest exists.")
    if existing_manifest is not None and existing_manifest.status == "completed":
        raise OrchestratorError(
            f"Cannot resume run_id {run_id!r}: the run is already completed."
        )

    running_manifest: RunManifest | None = None
    try:
        if existing_manifest is None:
            print_stage("ingestion", f"source={source_path} run_id={run_id}")
            document = await ingest_document(source_path, audit_store=audit_store)
            print_stage(
                "ingestion.done",
                f"doc_id={document.doc_id} bytes={document.text_byte_length}",
            )
            created_manifest = RunManifest(
                run_id=run_id,
                doc_id=document.doc_id,
                audit_db_path=str(audit_db_path),
                status="created",
                started_at=datetime.now(timezone.utc),
                output_data_point_ids=(),
            )
            await audit_store.record_run_manifest(created_manifest)
            running_manifest = transition_manifest(created_manifest, status="running")
        else:
            print_stage("resume", f"source={source_path} run_id={run_id}")
            document = await load_resume_document(
                source_path=source_path,
                manifest=existing_manifest,
                audit_store=audit_store,
            )
            print_stage(
                "resume.done",
                f"doc_id={document.doc_id} status={existing_manifest.status}",
            )
            running_manifest = transition_manifest(existing_manifest, status="running")

        await audit_store.update_run_manifest(running_manifest)
        await ensure_stage_completed(audit_store, run_id=run_id, stage="ingestion")
        return document, running_manifest
    except Exception:
        if running_manifest is not None:
            await mark_run_failed(audit_store, running_manifest=running_manifest)
        raise


async def mark_run_failed(
    audit_store: AuditStore,
    *,
    running_manifest: RunManifest,
) -> None:
    failed_manifest = transition_manifest(
        running_manifest,
        status="failed",
        completed_at=datetime.now(timezone.utc),
    )
    await audit_store.update_run_manifest(failed_manifest)


__all__ = ["mark_run_failed", "start_or_resume_run"]
