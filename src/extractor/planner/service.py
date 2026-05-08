from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel
from pydantic import ValidationError

from extractor.audit import AuditStore
from extractor.config import ChunkingConfig
from extractor.contracts import (
    ApprovedSchemaArtifact,
    CategoryDefinition,
    Chunk,
    ChunkPolicy,
    Document,
    ExtractionPlan,
    FieldDefinition,
)
from extractor.contracts.models import LLMStage
from extractor.llm import LLMClient, PromptLoader, StructuredLLMRequest
from extractor.llm.payloads import split_model_json_before_field
from extractor.planner.models import (
    BudgetAllocation,
    DocumentClassification,
    PlanningStageInput,
    SchemaCritique,
    SchemaProposal,
    StrategySelection,
)
from extractor.planner.schema_registry import select_schema_registry_candidates


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
    approved_schema_artifacts: tuple[ApprovedSchemaArtifact, ...] = (),
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
    selected_schema = _select_reusable_schema(
        approved_schema_artifacts=approved_schema_artifacts,
        document_class=classification.document_type,
        domain_hints=merged_domain_hints,
    )

    if selected_schema is None:
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
        schema_critique = schema_critique.model_copy(
            update={
                "approved_categories": _generalize_schema_descriptions(
                    schema_critique.approved_categories,
                )
            },
        )
        plan_domain_hints = merged_domain_hints
        schema_metadata = None
    else:
        schema_proposal = None
        schema_critique = SchemaCritique(
            accepted=True,
            approved_categories=selected_schema.approved_categories,
            issues=(),
        )
        plan_domain_hints = selected_schema.domain_hints
        schema_metadata = selected_schema.schema_metadata

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
        plan_input = {
            "run_id": run_id,
            "doc_id": document.doc_id,
            "domain_hints": plan_domain_hints,
            "approved_categories": schema_critique.approved_categories,
            "enabled_lenses": strategy.enabled_lenses,
            "chunk_policy": ChunkPolicy(
                window_tokens=chunking_config.window_tokens,
                overlap_tokens=chunking_config.overlap_tokens,
            ),
            "budget": budget.budget,
        }
        if schema_metadata is not None:
            plan_input["schema_metadata"] = schema_metadata
        plan = ExtractionPlan(**plan_input)
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
    stable_user_prefix, user_content = split_model_json_before_field(
        stage_input,
        "domain_hints",
    )
    result = await llm_client.complete_structured(
        StructuredLLMRequest(
            run_id=run_id,
            stage=stage,
            prompt=prompt,
            user_content=user_content,
            stable_user_prefix=stable_user_prefix,
            prompt_cache_allowed=False,
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


def _select_reusable_schema(
    *,
    approved_schema_artifacts: tuple[ApprovedSchemaArtifact, ...],
    document_class: str,
    domain_hints: tuple[str, ...],
) -> ApprovedSchemaArtifact | None:
    candidates = select_schema_registry_candidates(
        approved_schema_artifacts,
        document_class=document_class,
        domain_hints=domain_hints,
    )
    if len(candidates) == 1:
        return candidates[0]
    return None


def _generalize_schema_descriptions(
    categories: tuple[CategoryDefinition, ...],
) -> tuple[CategoryDefinition, ...]:
    generalized = tuple(_generalize_category_description(category) for category in categories)
    return tuple(_ensure_operational_metric_facility_field(category) for category in generalized)


def _generalize_category_description(category: CategoryDefinition) -> CategoryDefinition:
    description = category.description
    if category.name == "CorporateEvent":
        description = (
            "Source-backed significant corporate or business events, including "
            "acquisitions, approvals, facility commencements or operation starts, "
            "transactions, financings, restructurings, or other stated corporate "
            "actions. Use exact source evidence for each approved field; examples "
            "in the document are illustrative and do not reserve this category for "
            "one named event or transaction."
        )
    fields = tuple(_generalize_field_description(field) for field in category.fields)
    return category.model_copy(update={"description": description, "fields": fields})


def _generalize_field_description(field: FieldDefinition) -> FieldDefinition:
    if field.name == "facility":
        return field.model_copy(
            update={
                "description": (
                    "The bare source-stated facility or asset name associated with "
                    "the fact. Include location or descriptive qualifiers only when "
                    "the field name or approved role explicitly requires facility "
                    "plus location; otherwise a source-backed bare name is sufficient."
                )
            }
        )

    if field.name.endswith("_type"):
        return field.model_copy(
            update={
                "description": _append_description_sentence(
                    field.description,
                    (
                        "Prefer a concise source-traced label for the field value; "
                        "noun-form normalization is allowed and preferred when the "
                        "source words support the same action or type, while "
                        "provenance stays on the supporting source words."
                    ),
                )
            }
        )

    return field


def _ensure_operational_metric_facility_field(
    category: CategoryDefinition,
) -> CategoryDefinition:
    if category.name != "OperationalMetric":
        return category
    if any(field.name == "facility" for field in category.fields):
        return category

    facility_field = FieldDefinition(
        name="facility",
        description=(
            "The bare source-stated facility or asset name associated with a "
            "facility-specific operational metric. Populate only when the "
            "source ties the metric to a named facility or asset; leave absent "
            "for fleet-wide or company-wide operational metrics."
        ),
        value_type="text",
        required=False,
    )
    return category.model_copy(update={"fields": (*category.fields, facility_field)})


def _append_description_sentence(description: str, sentence: str) -> str:
    if sentence in description:
        return description
    separator = "" if description.endswith((".", "!", "?")) else "."
    return f"{description}{separator} {sentence}"


__all__ = ["PlanningError", "create_extraction_plan"]
