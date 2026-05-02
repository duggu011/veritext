"""Run the pipeline through executor, then stop.

This diagnostic runner is for checking whether ingestion, chunking, planning,
and executor candidate production look healthy before paying for critic,
verifier, reconciler, and reporter calls.

It writes normal audit rows and leaves the run manifest in a resumable
non-completed state. After review, continue the same run with:

    PYTHONPATH=src python3 -m extractor.cli <source> --output <out>.json \
        --run-id <run_id> --resume
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from extractor.audit import (
    AuditStore,
    CandidateRejection,
    RunStageName,
    RunStageState,
)
from extractor.chunker import chunk_document
from extractor.config import ConfigError, ExtractorConfig, configure_logging, load_config
from extractor.contracts import (
    Chunk,
    Document,
    ExtractionPlan,
    LensCandidate,
    RunManifest,
)
from extractor.executor import ExecutionResult, execute_plan
from extractor.ingestion import ingest_document
from extractor.llm import LLMClient, PromptLoader
from extractor.orchestrator.service import OrchestratorError
from extractor.planner import PlanningError, create_extraction_plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="debug_executor_only",
        description="Run ingest + chunk + planner + executor and stop.",
    )
    parser.add_argument("source", type=Path, help="Source document path.")
    parser.add_argument(
        "--run-id",
        required=True,
        help=(
            "Stable run id. Use the same id later with `extractor.cli --resume` "
            "to continue after executor."
        ),
    )
    parser.add_argument(
        "--debug-dir",
        type=Path,
        default=None,
        help="Directory for JSON artifacts. Default: .veritext/debug/<run-id>/",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing default.yaml and optional local.yaml.",
    )
    parser.add_argument(
        "--no-local-config",
        action="store_true",
        help="Ignore config/local.yaml even when it exists.",
    )
    parser.add_argument(
        "--domain-hint",
        action="append",
        default=[],
        help="Domain hint to pass to planning. May be repeated.",
    )
    return parser


def _dump_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(payload, "model_dump"):
        data = payload.model_dump(mode="json")  # type: ignore[union-attr]
    else:
        data = payload
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str))
    print(f"  wrote {path}")


async def _record_stage(
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


async def async_main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.source.is_file():
        raise SystemExit(f"Source document does not exist: {args.source}")

    config = load_config(
        config_dir=args.config_dir,
        include_local=not args.no_local_config,
    )
    configure_logging(config.logging)

    debug_dir = args.debug_dir or Path(".veritext/debug") / args.run_id
    debug_dir.mkdir(parents=True, exist_ok=True)

    prompt_loader = PromptLoader(config.prompts.directory)
    llm_client = LLMClient(config.llm)
    domain_hints = tuple(args.domain_hint)

    print(f"== Run id:      {args.run_id}")
    print(f"== Source:      {args.source}")
    print("== Stop after:  executor")
    print(f"== Debug dir:   {debug_dir}")
    print()

    async with AuditStore(config.audit.database_path) as audit_store:
        manifest = await audit_store.get_run_manifest(args.run_id)
        if manifest is None:
            document, chunks, plan = await _run_prerequisites(
                source=args.source,
                run_id=args.run_id,
                domain_hints=domain_hints,
                debug_dir=debug_dir,
                audit_store=audit_store,
                config=config,
                prompt_loader=prompt_loader,
                llm_client=llm_client,
            )
        else:
            document, chunks, plan = await _load_existing_prerequisites(
                source=args.source,
                manifest=manifest,
                run_id=args.run_id,
                audit_store=audit_store,
            )

        execution = await _run_or_load_executor(
            run_id=args.run_id,
            plan=plan,
            chunks=chunks,
            prompt_loader=prompt_loader,
            llm_client=llm_client,
            audit_store=audit_store,
            config=config,
        )

    _dump_executor_artifacts(debug_dir=debug_dir, execution=execution, plan=plan)
    print()
    print("== Done. Stopped after: executor ==")
    print(f"Artifacts in: {debug_dir}")
    print()
    print("To continue this run through critic/verifier/reconciler/reporter:")
    print(
        "  PYTHONPATH=src python3 -m extractor.cli "
        f"{args.source} --output outputs/{args.run_id}.json "
        f"--run-id {args.run_id} --resume"
    )
    return 0


async def _run_prerequisites(
    *,
    source: Path,
    run_id: str,
    domain_hints: tuple[str, ...],
    debug_dir: Path,
    audit_store: AuditStore,
    config: ExtractorConfig,
    prompt_loader: PromptLoader,
    llm_client: LLMClient,
) -> tuple[Document, tuple[Chunk, ...], ExtractionPlan]:
    print("== Stage 1: ingestion ==")
    document = await ingest_document(source, audit_store=audit_store)
    _dump_json(debug_dir / "00_document.json", document)
    manifest = RunManifest(
        run_id=run_id,
        doc_id=document.doc_id,
        audit_db_path=str(config.audit.database_path),
        status="running",
        started_at=datetime.now(timezone.utc),
        output_data_point_ids=(),
    )
    await audit_store.record_run_manifest(manifest)
    await _record_stage(audit_store, run_id=run_id, stage="ingestion")

    print("\n== Stage 2: chunking ==")
    chunks = await chunk_document(document, config.chunking, audit_store=audit_store)
    _dump_json(
        debug_dir / "01_chunks.json",
        {"chunks": [chunk.model_dump(mode="json") for chunk in chunks]},
    )
    await _record_stage(audit_store, run_id=run_id, stage="chunker")

    print("\n== Stage 3: planner ==")
    plan = await create_extraction_plan(
        run_id=run_id,
        document=document,
        chunks=chunks,
        chunking_config=config.chunking,
        prompt_loader=prompt_loader,
        llm_client=llm_client,
        domain_hints=domain_hints,
        audit_store=audit_store,
    )
    _dump_json(debug_dir / "02_extraction_plan.json", plan)
    await _record_stage(audit_store, run_id=run_id, stage="planner")
    return document, chunks, plan


async def _load_existing_prerequisites(
    *,
    source: Path,
    manifest: RunManifest,
    run_id: str,
    audit_store: AuditStore,
) -> tuple[Document, tuple[Chunk, ...], ExtractionPlan]:
    if manifest.status == "completed":
        raise OrchestratorError(
            f"Run {run_id!r} is already completed; choose a new --run-id."
        )
    print("== Existing run found: loading audited prerequisites ==")
    document = await ingest_document(source, audit_store=None)
    if document.doc_id != manifest.doc_id:
        raise OrchestratorError(
            f"Source doc_id {document.doc_id} does not match run manifest "
            f"doc_id {manifest.doc_id}."
        )

    stored_document = await audit_store.get_document(manifest.doc_id)
    if stored_document is not None:
        document = stored_document
    chunks = await audit_store.list_chunks(document.doc_id)
    if not chunks:
        raise OrchestratorError(
            f"Run {run_id!r} has no audited chunks; start a fresh executor debug run."
        )
    plan = await audit_store.get_extraction_plan(run_id)
    if plan is None:
        raise OrchestratorError(
            f"Run {run_id!r} has no audited extraction plan; run planner first."
        )
    print(f"  loaded chunks={len(chunks)} lenses={list(plan.enabled_lenses)}")
    return document, chunks, plan


async def _run_or_load_executor(
    *,
    run_id: str,
    plan: ExtractionPlan,
    chunks: tuple[Chunk, ...],
    prompt_loader: PromptLoader,
    llm_client: LLMClient,
    audit_store: AuditStore,
    config: ExtractorConfig,
) -> ExecutionResult:
    existing_candidates = await audit_store.list_lens_candidates(run_id)
    existing_rejections = await audit_store.list_candidate_rejections_for_run(run_id)
    executor_state = await audit_store.get_run_stage_state(run_id, "executor")
    if existing_candidates or executor_state is not None:
        print("\n== Stage 4: executor already audited; loading existing candidates ==")
        executor_rejections = tuple(
            rejection for rejection in existing_rejections if rejection.stage == "executor"
        )
        rejected_ids = {rejection.candidate_id for rejection in executor_rejections}
        rejected = tuple(
            candidate
            for candidate in existing_candidates
            if candidate.candidate_id in rejected_ids
        )
        accepted = tuple(
            candidate
            for candidate in existing_candidates
            if candidate.candidate_id not in rejected_ids
        )
        return ExecutionResult(
            accepted_candidates=accepted,
            rejected_candidates=rejected,
            rejections=executor_rejections,
        )

    print("\n== Stage 4: executor ==")
    execution = await execute_plan(
        plan=plan,
        chunks=chunks,
        prompt_loader=prompt_loader,
        llm_client=llm_client,
        execution_config=config.execution,
        audit_store=audit_store,
    )
    await _record_stage(audit_store, run_id=run_id, stage="executor")
    return execution


def _dump_executor_artifacts(
    *,
    debug_dir: Path,
    execution: ExecutionResult,
    plan: ExtractionPlan,
) -> None:
    candidates = execution.accepted_candidates + execution.rejected_candidates
    field_counts = Counter(
        f"{candidate.lens}.{candidate.category}.{candidate.field_name}"
        for candidate in execution.accepted_candidates
    )
    rejection_counts = Counter(
        reason.code for rejection in execution.rejections for reason in rejection.reasons
    )
    summary = {
        "run_id": plan.run_id,
        "doc_id": plan.doc_id,
        "enabled_lenses": list(plan.enabled_lenses),
        "category_count": len(plan.approved_categories),
        "accepted_candidate_count": len(execution.accepted_candidates),
        "rejected_candidate_count": len(execution.rejected_candidates),
        "rejection_count": len(execution.rejections),
        "accepted_by_lens_category_field": dict(sorted(field_counts.items())),
        "rejections_by_code": dict(sorted(rejection_counts.items())),
    }
    _dump_json(debug_dir / "03_executor_summary.json", summary)
    _dump_json(
        debug_dir / "04_executor_candidates.json",
        {"candidates": [_candidate_json(candidate) for candidate in candidates]},
    )
    _dump_json(
        debug_dir / "05_executor_rejections.json",
        {"rejections": [_rejection_json(rejection) for rejection in execution.rejections]},
    )


def _candidate_json(candidate: LensCandidate) -> dict[str, object]:
    return candidate.model_dump(mode="json")


def _rejection_json(rejection: CandidateRejection) -> dict[str, object]:
    return rejection.model_dump(mode="json")


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return asyncio.run(async_main(argv))
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130
    except (ConfigError, OrchestratorError, PlanningError) as exc:
        print(f"{exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
