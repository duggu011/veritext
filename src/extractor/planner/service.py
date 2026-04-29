from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel
from pydantic import ValidationError

from extractor.audit import AuditStore
from extractor.config import ChunkingConfig
from extractor.contracts import Chunk, ChunkPolicy, Document, ExtractionPlan
from extractor.contracts.models import LLMStage
from extractor.llm import LLMClient, PromptLoader, StructuredLLMRequest
from extractor.planner.models import (
    BudgetAllocation,
    DocumentClassification,
    PlanningStageInput,
    SchemaCritique,
    SchemaProposal,
    StrategySelection,
)


OutputModelT = TypeVar("OutputModelT", bound=BaseModel)


class PlanningError(RuntimeError):
    """Raised when extraction planning cannot produce a valid auditable plan."""


async def create_extraction_plan(
    *,
    run_id: str,
    document: Document,
    chunks: tuple[Chunk, ...],
    chunking_config: ChunkingConfig,
    prompt_loader: PromptLoader,
    llm_client: LLMClient,
    domain_hints: tuple[str, ...] = (),
    audit_store: AuditStore | None = None,
) -> ExtractionPlan:
    _validate_chunk_inputs(document, chunks)

    classification = await _call_planning_stage(
        run_id=run_id,
        stage="planner.classify_document",
        tool_name="classify_document",
        tool_description="Classify the source document for extraction planning.",
        prompt_loader=prompt_loader,
        llm_client=llm_client,
        audit_store=audit_store,
        output_model=DocumentClassification,
        stage_input=PlanningStageInput(
            run_id=run_id,
            document=document,
            chunks=chunks,
            domain_hints=domain_hints,
        ),
    )
    merged_domain_hints = _merge_domain_hints(domain_hints, classification.domain_hints)

    schema_proposal = await _call_planning_stage(
        run_id=run_id,
        stage="planner.propose_schema",
        tool_name="propose_schema",
        tool_description="Propose extraction categories and fields.",
        prompt_loader=prompt_loader,
        llm_client=llm_client,
        audit_store=audit_store,
        output_model=SchemaProposal,
        stage_input=PlanningStageInput(
            run_id=run_id,
            document=document,
            chunks=chunks,
            domain_hints=merged_domain_hints,
            classification=classification,
        ),
    )

    schema_critique = await _call_planning_stage(
        run_id=run_id,
        stage="planner.critique_schema",
        tool_name="critique_schema",
        tool_description="Critique and approve the proposed extraction schema.",
        prompt_loader=prompt_loader,
        llm_client=llm_client,
        audit_store=audit_store,
        output_model=SchemaCritique,
        stage_input=PlanningStageInput(
            run_id=run_id,
            document=document,
            chunks=chunks,
            domain_hints=merged_domain_hints,
            classification=classification,
            schema_proposal=schema_proposal,
        ),
    )
    if not schema_critique.accepted:
        raise PlanningError(
            "Schema critique rejected the proposed schema: "
            + "; ".join(schema_critique.issues)
        )

    strategy = await _call_planning_stage(
        run_id=run_id,
        stage="planner.select_strategy",
        tool_name="select_strategy",
        tool_description="Select extraction lenses for the approved schema.",
        prompt_loader=prompt_loader,
        llm_client=llm_client,
        audit_store=audit_store,
        output_model=StrategySelection,
        stage_input=PlanningStageInput(
            run_id=run_id,
            document=document,
            chunks=chunks,
            domain_hints=merged_domain_hints,
            classification=classification,
            schema_proposal=schema_proposal,
            schema_critique=schema_critique,
        ),
    )

    budget = await _call_planning_stage(
        run_id=run_id,
        stage="planner.allocate_budget",
        tool_name="allocate_budget",
        tool_description="Allocate bounded LLM call budgets for selected lenses.",
        prompt_loader=prompt_loader,
        llm_client=llm_client,
        audit_store=audit_store,
        output_model=BudgetAllocation,
        stage_input=PlanningStageInput(
            run_id=run_id,
            document=document,
            chunks=chunks,
            domain_hints=merged_domain_hints,
            classification=classification,
            schema_proposal=schema_proposal,
            schema_critique=schema_critique,
            strategy=strategy,
        ),
    )

    try:
        plan = ExtractionPlan(
            run_id=run_id,
            doc_id=document.doc_id,
            domain_hints=merged_domain_hints,
            approved_categories=schema_critique.approved_categories,
            enabled_lenses=strategy.enabled_lenses,
            chunk_policy=ChunkPolicy(
                window_tokens=chunking_config.window_tokens,
                overlap_tokens=chunking_config.overlap_tokens,
            ),
            budget=budget.budget,
        )
    except ValidationError as exc:
        raise PlanningError(f"Invalid extraction plan: {exc}") from exc

    if audit_store is not None:
        await audit_store.record_extraction_plan(plan)
    return plan


async def _call_planning_stage(
    *,
    run_id: str,
    stage: LLMStage,
    tool_name: str,
    tool_description: str,
    prompt_loader: PromptLoader,
    llm_client: LLMClient,
    audit_store: AuditStore | None,
    output_model: type[OutputModelT],
    stage_input: PlanningStageInput,
) -> OutputModelT:
    prompt = prompt_loader.load(stage)
    result = await llm_client.complete_structured(
        StructuredLLMRequest(
            run_id=run_id,
            stage=stage,
            prompt=prompt,
            user_content=stage_input.model_dump_json(),
            tool_name=tool_name,
            tool_description=tool_description,
        ),
        output_model=output_model,
        audit_store=audit_store,
    )
    return result.output


def _validate_chunk_inputs(document: Document, chunks: tuple[Chunk, ...]) -> None:
    if not chunks:
        raise PlanningError("planning requires at least one chunk")
    for chunk in chunks:
        if chunk.doc_id != document.doc_id:
            raise PlanningError("chunk doc_id must match document doc_id")


def _merge_domain_hints(
    requested_hints: tuple[str, ...],
    classified_hints: tuple[str, ...],
) -> tuple[str, ...]:
    merged: list[str] = []
    for hint in (*requested_hints, *classified_hints):
        if hint not in merged:
            merged.append(hint)
    return tuple(merged)


__all__ = ["PlanningError", "create_extraction_plan"]
