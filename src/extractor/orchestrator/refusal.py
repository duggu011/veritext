from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from extractor.audit import AuditStore, RunStageState
from extractor.config import SchemaRegistryConfig
from extractor.contracts import (
    Chunk,
    Document,
    PlanningRefusal,
    RunManifest,
    SchemaSelectionPolicy,
)
from extractor.orchestrator.models import PipelineRefusalResult
from extractor.reporter import write_refusal_report


def schema_selection_policy_from_config(
    config: SchemaRegistryConfig,
) -> SchemaSelectionPolicy:
    return SchemaSelectionPolicy(
        require_approved_schema=config.require_approved_schema,
        minimum_schema_coverage=config.minimum_schema_coverage,
        allow_planner_generated_fallback=not config.require_approved_schema,
    )


async def complete_planner_refusal(
    *,
    run_id: str,
    document: Document,
    chunks: tuple[Chunk, ...],
    running_manifest: RunManifest,
    refusal: PlanningRefusal,
    output_path: str | Path,
    audit_store: AuditStore,
) -> PipelineRefusalResult:
    await audit_store.record_run_stage_state(
        RunStageState(
            run_id=run_id,
            stage="planner",
            completed_at=datetime.now(timezone.utc),
            planning_refusal=refusal,
        )
    )
    report = await write_refusal_report(
        manifest=running_manifest,
        refusal=refusal,
        output_path=output_path,
        audit_store=audit_store,
    )
    await audit_store.record_run_stage_state(
        RunStageState(
            run_id=run_id,
            stage="reporter",
            completed_at=datetime.now(timezone.utc),
        )
    )
    usage_summary = await audit_store.summarize_run(run_id)
    return PipelineRefusalResult(
        run_id=run_id,
        document=document,
        chunks=chunks,
        refusal=refusal,
        report=report,
        completed_manifest=report.completed_manifest,
        usage_summary=usage_summary,
    )


__all__ = ["complete_planner_refusal", "schema_selection_policy_from_config"]
