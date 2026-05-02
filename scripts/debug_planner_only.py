"""Run only the planner stages of the pipeline, then stop.

Diagnostic script for inspecting planner output (classify -> propose ->
critique -> strategy -> budget) without paying for executor + critic +
verifier + reconciler. Each sub-stage's structured output is dumped as JSON
so the operator can review whether the planner produced the right schema
before any downstream stage runs.

After this script completes, the regular CLI can pick up from the executor
with the same run-id::

    PYTHONPATH=src python3 -m extractor.cli <source> --output <out>.json \\
        --run-id <run_id> --resume

This is allowed because the script records the same `run_stage_state` and
`extraction_plans` rows that the orchestrator writes on a normal run, so
`--resume` will skip ingestion / chunker / planner and continue at executor.

Usage::

    PYTHONPATH=src python3 scripts/debug_planner_only.py \\
        evals/fixtures/medium_research_brief/source.md \\
        --run-id medium-research-debug-1 \\
        --stop-after planner

`--stop-after` controls how far the planner is allowed to run::

    classify   -- stop after planner.classify_document
    propose    -- stop after planner.propose_schema
    critique   -- stop after planner.critique_schema
    strategy   -- stop after planner.select_strategy
    budget     -- stop after planner.allocate_budget (no ExtractionPlan saved)
    planner    -- run all five and persist the ExtractionPlan (default)

Stopping before `planner` means no ExtractionPlan row is written, so
`--resume` will not work for that run-id; you would need to start a new run.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from extractor.audit import AuditStore, RunStageName, RunStageState
from extractor.chunker import chunk_document
from extractor.config import ConfigError, configure_logging, load_config
from extractor.contracts import ChunkPolicy, ExtractionPlan, RunManifest
from extractor.ingestion import ingest_document
from extractor.llm import LLMClient, PromptLoader
from extractor.planner import (
    BudgetAllocation,
    DocumentClassification,
    PlanningError,
    PlanningStageInput,
    SchemaCritique,
    SchemaProposal,
    StrategySelection,
)
from extractor.planner.service import _call_planning_stage, _generalize_schema_descriptions


_STOP_POINTS = ("classify", "propose", "critique", "strategy", "budget", "planner")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="debug_planner_only",
        description=(
            "Run ingest + chunk + planner sub-stages and stop before the "
            "executor. Dumps each planner output as JSON for review."
        ),
    )
    parser.add_argument("source", type=Path, help="Source document path.")
    parser.add_argument(
        "--run-id",
        required=True,
        help="Stable run id. Use the same id later with `extractor.cli --resume` "
        "to continue from the executor.",
    )
    parser.add_argument(
        "--stop-after",
        choices=_STOP_POINTS,
        default="planner",
        help="Last planner sub-stage to run. Default: planner (run all five).",
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


def _merge_domain_hints(
    requested: tuple[str, ...],
    classified: tuple[str, ...],
) -> tuple[str, ...]:
    merged: list[str] = []
    for hint in (*requested, *classified):
        if hint not in merged:
            merged.append(hint)
    return tuple(merged)


def _dump_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(payload, "model_dump"):
        data = payload.model_dump(mode="json")  # type: ignore[union-attr]
    else:
        data = payload
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str))
    print(f"  wrote {path}")


async def _record_stage(
    audit_store: AuditStore, *, run_id: str, stage: RunStageName
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
    print(f"== Stop after:  {args.stop_after}")
    print(f"== Debug dir:   {debug_dir}")
    print()

    async with AuditStore(config.audit.database_path) as audit_store:
        existing = await audit_store.get_run_manifest(args.run_id)
        if existing is not None:
            raise SystemExit(
                f"run id {args.run_id!r} already exists in audit DB. "
                "Choose a different --run-id; this script does not resume "
                "debug runs."
            )

        # 1. Ingestion
        print("== Stage 1: ingestion ==")
        document = await ingest_document(args.source, audit_store=audit_store)
        _dump_json(debug_dir / "00_document.json", document)
        manifest = RunManifest(
            run_id=args.run_id,
            doc_id=document.doc_id,
            audit_db_path=str(config.audit.database_path),
            status="running",
            started_at=datetime.now(timezone.utc),
            output_data_point_ids=(),
        )
        await audit_store.record_run_manifest(manifest)
        await _record_stage(audit_store, run_id=args.run_id, stage="ingestion")

        # 2. Chunking
        print("\n== Stage 2: chunking ==")
        chunks = await chunk_document(
            document, config.chunking, audit_store=audit_store
        )
        _dump_json(
            debug_dir / "01_chunks.json",
            {"chunks": [c.model_dump(mode="json") for c in chunks]},
        )
        await _record_stage(audit_store, run_id=args.run_id, stage="chunker")

        # 3. Planner sub-stages, one at a time, with dump + stop checks.
        print("\n== Stage 3: planner ==")

        classification = await _call_planning_stage(
            run_id=args.run_id,
            stage="planner.classify_document",
            tool_name="classify_document",
            tool_description="Classify the source document for extraction planning.",
            prompt_loader=prompt_loader,
            llm_client=llm_client,
            audit_store=audit_store,
            output_model=DocumentClassification,
            stage_input=PlanningStageInput(
                run_id=args.run_id,
                document=document,
                chunks=chunks,
                domain_hints=domain_hints,
            ),
        )
        _dump_json(debug_dir / "02_classification.json", classification)
        if args.stop_after == "classify":
            return _stopped(args.stop_after, debug_dir, allow_resume=False)

        merged_hints = _merge_domain_hints(domain_hints, classification.domain_hints)

        proposal = await _call_planning_stage(
            run_id=args.run_id,
            stage="planner.propose_schema",
            tool_name="propose_schema",
            tool_description="Propose extraction categories and fields.",
            prompt_loader=prompt_loader,
            llm_client=llm_client,
            audit_store=audit_store,
            output_model=SchemaProposal,
            stage_input=PlanningStageInput(
                run_id=args.run_id,
                document=document,
                chunks=chunks,
                domain_hints=merged_hints,
                classification=classification,
            ),
        )
        _dump_json(debug_dir / "03_schema_proposal.json", proposal)
        if args.stop_after == "propose":
            return _stopped(args.stop_after, debug_dir, allow_resume=False)

        critique = await _call_planning_stage(
            run_id=args.run_id,
            stage="planner.critique_schema",
            tool_name="critique_schema",
            tool_description="Critique and approve the proposed extraction schema.",
            prompt_loader=prompt_loader,
            llm_client=llm_client,
            audit_store=audit_store,
            output_model=SchemaCritique,
            stage_input=PlanningStageInput(
                run_id=args.run_id,
                document=document,
                chunks=chunks,
                domain_hints=merged_hints,
                classification=classification,
                schema_proposal=proposal,
            ),
        )
        _dump_json(debug_dir / "04_schema_critique.json", critique)
        if args.stop_after == "critique":
            return _stopped(args.stop_after, debug_dir, allow_resume=False)
        if not critique.accepted:
            raise PlanningError(
                "Schema critique rejected the proposed schema: "
                + "; ".join(critique.issues)
            )
        critique = critique.model_copy(
            update={
                "approved_categories": _generalize_schema_descriptions(
                    critique.approved_categories,
                )
            },
        )
        _dump_json(debug_dir / "04_schema_critique.generalized.json", critique)

        strategy = await _call_planning_stage(
            run_id=args.run_id,
            stage="planner.select_strategy",
            tool_name="select_strategy",
            tool_description="Select extraction lenses for the approved schema.",
            prompt_loader=prompt_loader,
            llm_client=llm_client,
            audit_store=audit_store,
            output_model=StrategySelection,
            stage_input=PlanningStageInput(
                run_id=args.run_id,
                document=document,
                chunks=chunks,
                domain_hints=merged_hints,
                classification=classification,
                schema_proposal=proposal,
                schema_critique=critique,
            ),
        )
        _dump_json(debug_dir / "05_strategy.json", strategy)
        if args.stop_after == "strategy":
            return _stopped(args.stop_after, debug_dir, allow_resume=False)

        budget = await _call_planning_stage(
            run_id=args.run_id,
            stage="planner.allocate_budget",
            tool_name="allocate_budget",
            tool_description="Allocate bounded LLM call budgets for selected lenses.",
            prompt_loader=prompt_loader,
            llm_client=llm_client,
            audit_store=audit_store,
            output_model=BudgetAllocation,
            stage_input=PlanningStageInput(
                run_id=args.run_id,
                document=document,
                chunks=chunks,
                domain_hints=merged_hints,
                classification=classification,
                schema_proposal=proposal,
                schema_critique=critique,
                strategy=strategy,
            ),
        )
        _dump_json(debug_dir / "06_budget.json", budget)
        if args.stop_after == "budget":
            return _stopped(args.stop_after, debug_dir, allow_resume=False)

        # 4. Persist ExtractionPlan + planner stage state so --resume works.
        plan = ExtractionPlan(
            run_id=args.run_id,
            doc_id=document.doc_id,
            domain_hints=merged_hints,
            approved_categories=critique.approved_categories,
            enabled_lenses=strategy.enabled_lenses,
            chunk_policy=ChunkPolicy(
                window_tokens=config.chunking.window_tokens,
                overlap_tokens=config.chunking.overlap_tokens,
            ),
            budget=budget.budget,
        )
        await audit_store.record_extraction_plan(plan)
        _dump_json(debug_dir / "07_extraction_plan.json", plan)
        await _record_stage(audit_store, run_id=args.run_id, stage="planner")
        return _stopped(args.stop_after, debug_dir, allow_resume=True)


def _stopped(stop_after: str, debug_dir: Path, *, allow_resume: bool) -> int:
    print()
    print(f"== Done. Stopped after: {stop_after} ==")
    print(f"Artifacts in: {debug_dir}")
    if allow_resume:
        print()
        print("To continue from the executor with the same run id:")
        print(
            "  PYTHONPATH=src python3 -m extractor.cli <source> "
            "--output <out>.json --run-id <same-run-id> --resume"
        )
    else:
        print()
        print(
            "Stopped before the ExtractionPlan was persisted. "
            "Resume is NOT possible for this run id."
        )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return asyncio.run(async_main(argv))
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130
    except (ConfigError, PlanningError) as exc:
        print(f"{exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
