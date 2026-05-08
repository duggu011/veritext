from __future__ import annotations

from pathlib import Path

from extractor.audit import AuditStore
from extractor.config import ChunkingConfig, SchemaRegistryConfig
from extractor.contracts import ApprovedSchemaArtifact, Chunk, Document, ExtractionPlan, RunManifest
from extractor.llm import LLMClient, PromptLoader
from extractor.orchestrator.errors import OrchestratorError
from extractor.orchestrator.models import PipelineRefusalResult
from extractor.orchestrator.refusal import (
    complete_planner_refusal,
    schema_selection_policy_from_config,
)
from extractor.orchestrator.state import validate_resume_plan
from extractor.orchestrator.trace import print_stage
from extractor.planner import PlanningRefusalError, create_extraction_plan


async def plan_or_refuse(
    *,
    run_id: str,
    document: Document,
    chunks: tuple[Chunk, ...],
    chunking_config: ChunkingConfig,
    prompt_loader: PromptLoader,
    llm_client: LLMClient,
    domain_hints: tuple[str, ...],
    approved_schema_artifacts: tuple[ApprovedSchemaArtifact, ...],
    schema_registry_config: SchemaRegistryConfig,
    output_path: str | Path,
    running_manifest: RunManifest,
    audit_store: AuditStore,
) -> ExtractionPlan | PipelineRefusalResult:
    stored_plan = await audit_store.get_extraction_plan(run_id)
    planner_state = await audit_store.get_run_stage_state(run_id, "planner")
    if stored_plan is not None:
        plan = validate_resume_plan(
            plan=stored_plan,
            document=document,
            chunking_config=chunking_config,
        )
        print_stage("planner.resume", f"lenses={list(plan.enabled_lenses)}")
        return plan
    if planner_state is not None:
        if planner_state.planning_refusal is not None:
            raise OrchestratorError(
                f"Cannot resume: planner previously refused extraction for run {run_id}."
            )
        raise OrchestratorError(
            "Cannot resume: planner is marked complete but no extraction "
            f"plan exists for run {run_id}."
        )

    print_stage("planner", f"domain_hints={list(domain_hints) or 'none'}")
    try:
        return await create_extraction_plan(
            run_id=run_id,
            document=document,
            chunks=chunks,
            chunking_config=chunking_config,
            prompt_loader=prompt_loader,
            llm_client=llm_client,
            domain_hints=domain_hints,
            approved_schema_artifacts=approved_schema_artifacts,
            schema_selection_policy=schema_selection_policy_from_config(
                schema_registry_config
            ),
            audit_store=audit_store,
        )
    except PlanningRefusalError as exc:
        print_stage("planner.refused", f"reasons={list(exc.refusal.reason_codes)}")
        return await complete_planner_refusal(
            run_id=run_id,
            document=document,
            chunks=chunks,
            running_manifest=running_manifest,
            refusal=exc.refusal,
            output_path=output_path,
            audit_store=audit_store,
        )


__all__ = ["plan_or_refuse"]
