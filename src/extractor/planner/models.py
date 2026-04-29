from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from extractor.contracts import (
    CategoryDefinition,
    Chunk,
    Document,
    ExtractionBudget,
)
from extractor.contracts.models import LensName


NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


class PlannerModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DocumentClassification(PlannerModel):
    document_type: NonEmptyStr
    summary: NonEmptyStr
    domain_hints: tuple[NonEmptyStr, ...]
    confidence: Confidence


class SchemaProposal(PlannerModel):
    categories: tuple[CategoryDefinition, ...] = Field(min_length=1)
    rationale: NonEmptyStr


class SchemaCritique(PlannerModel):
    accepted: bool = Field(strict=True)
    approved_categories: tuple[CategoryDefinition, ...]
    issues: tuple[NonEmptyStr, ...]

    @model_validator(mode="after")
    def validate_accepted_categories(self) -> SchemaCritique:
        if self.accepted and not self.approved_categories:
            raise ValueError("accepted schema critiques must include approved categories")
        if not self.accepted and not self.issues:
            raise ValueError("rejected schema critiques must include issues")
        return self


class StrategySelection(PlannerModel):
    enabled_lenses: tuple[LensName, ...] = Field(min_length=1)
    rationale: NonEmptyStr

    @model_validator(mode="after")
    def validate_unique_lenses(self) -> StrategySelection:
        if len(self.enabled_lenses) != len(set(self.enabled_lenses)):
            raise ValueError("enabled lenses must be unique")
        return self


class BudgetAllocation(PlannerModel):
    budget: ExtractionBudget


class PlanningStageInput(PlannerModel):
    run_id: NonEmptyStr
    document: Document
    chunks: tuple[Chunk, ...] = Field(min_length=1)
    domain_hints: tuple[NonEmptyStr, ...]
    classification: DocumentClassification | None = None
    schema_proposal: SchemaProposal | None = None
    schema_critique: SchemaCritique | None = None
    strategy: StrategySelection | None = None


__all__ = [
    "BudgetAllocation",
    "DocumentClassification",
    "PlanningStageInput",
    "SchemaCritique",
    "SchemaProposal",
    "StrategySelection",
]
