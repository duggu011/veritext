from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from extractor.contracts.base import Confidence, ContractModel, NonEmptyStr
from extractor.contracts.models import CategoryDefinition
from extractor.contracts.schema_metadata import (
    ApprovedSchemaMetadata,
    canonical_schema_hash,
)


PlanningRefusalReasonCode = Literal[
    "no_approved_schema_candidates",
    "ambiguous_schema_candidates",
    "coverage_below_threshold",
    "document_out_of_scope",
    "schema_hash_mismatch",
    "schema_registry_invalid",
]


class ApprovedSchemaArtifact(ContractModel):
    schema_metadata: ApprovedSchemaMetadata
    approved_categories: tuple[CategoryDefinition, ...] = Field(min_length=1)
    document_class: NonEmptyStr
    domain_hints: tuple[NonEmptyStr, ...] = ()
    match_basis: tuple[NonEmptyStr, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_artifact(self) -> ApprovedSchemaArtifact:
        if self.schema_metadata.source_kind != "schema_registry":
            raise ValueError("approved schema artifacts require schema_registry source_kind")
        if self.schema_metadata.document_class != self.document_class:
            raise ValueError("document_class must match schema_metadata document_class")
        if len(self.match_basis) != len(set(self.match_basis)):
            raise ValueError("match_basis entries must be unique")

        expected_schema_hash = canonical_schema_hash(
            approved_categories=self.approved_categories,
            source_kind=self.schema_metadata.source_kind,
            schema_version=self.schema_metadata.schema_version,
            domain_hints=self.domain_hints,
            domain_pack_id=self.schema_metadata.domain_pack_id,
            document_class=self.document_class,
        )
        if self.schema_metadata.schema_hash != expected_schema_hash:
            raise ValueError("schema_metadata schema_hash must match approved schema")
        return self

    @property
    def schema_id(self) -> str:
        return self.schema_metadata.schema_id


class SchemaSelectionPolicy(ContractModel):
    require_approved_schema: bool = Field(strict=True)
    minimum_schema_coverage: Confidence
    allow_planner_generated_fallback: bool = Field(strict=True)

    @model_validator(mode="after")
    def validate_fallback_policy(self) -> SchemaSelectionPolicy:
        if self.require_approved_schema and self.allow_planner_generated_fallback:
            raise ValueError(
                "allow_planner_generated_fallback must be false when approved schemas are required"
            )
        return self


class SchemaCoverageEstimate(ContractModel):
    schema_id: NonEmptyStr
    category_name: NonEmptyStr
    coverage: Confidence
    rationale: NonEmptyStr


class SchemaFitAssessment(ContractModel):
    schema_id: NonEmptyStr
    fits: bool = Field(strict=True)
    overall_coverage: Confidence
    coverage_estimates: tuple[SchemaCoverageEstimate, ...]
    reason_codes: tuple[PlanningRefusalReasonCode, ...] = ()

    @model_validator(mode="after")
    def validate_assessment(self) -> SchemaFitAssessment:
        for estimate in self.coverage_estimates:
            if estimate.schema_id != self.schema_id:
                raise ValueError("coverage estimate schema_id must match assessment schema_id")
        if not self.fits and not self.reason_codes:
            raise ValueError("non-fitting schema assessments require reason_codes")
        if self.fits and self.reason_codes:
            raise ValueError("fitting schema assessments must not include refusal reason_codes")
        return self


class SchemaSelection(ContractModel):
    document_class: NonEmptyStr
    domain_hints: tuple[NonEmptyStr, ...]
    candidate_schema_ids: tuple[NonEmptyStr, ...]
    selected_schema_id: NonEmptyStr | None = None
    match_basis: tuple[NonEmptyStr, ...]
    selected_coverage: Confidence | None = None
    fit_assessments: tuple[SchemaFitAssessment, ...] = ()

    @model_validator(mode="after")
    def validate_selection(self) -> SchemaSelection:
        if len(self.candidate_schema_ids) != len(set(self.candidate_schema_ids)):
            raise ValueError("candidate_schema_ids must be unique")
        candidates = set(self.candidate_schema_ids)
        if self.selected_schema_id is not None and self.selected_schema_id not in candidates:
            raise ValueError("selected_schema_id must be one of candidate_schema_ids")
        for assessment in self.fit_assessments:
            if assessment.schema_id not in candidates:
                raise ValueError("fit_assessment schema_id must be in candidate_schema_ids")
        if self.selected_schema_id is None and self.selected_coverage is not None:
            raise ValueError("selected_coverage requires selected_schema_id")
        return self


class PlanningRefusal(ContractModel):
    run_id: NonEmptyStr
    doc_id: NonEmptyStr
    document_class: NonEmptyStr
    domain_hints: tuple[NonEmptyStr, ...]
    policy: SchemaSelectionPolicy
    candidate_schema_ids: tuple[NonEmptyStr, ...]
    fit_assessments: tuple[SchemaFitAssessment, ...] = ()
    reason_codes: tuple[PlanningRefusalReasonCode, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_refusal(self) -> PlanningRefusal:
        if len(self.candidate_schema_ids) != len(set(self.candidate_schema_ids)):
            raise ValueError("candidate_schema_ids must be unique")
        candidates = set(self.candidate_schema_ids)
        for assessment in self.fit_assessments:
            if assessment.schema_id not in candidates:
                raise ValueError("fit_assessment schema_id must be in candidate_schema_ids")
        return self


__all__ = [
    "ApprovedSchemaArtifact",
    "PlanningRefusal",
    "PlanningRefusalReasonCode",
    "SchemaCoverageEstimate",
    "SchemaFitAssessment",
    "SchemaSelection",
    "SchemaSelectionPolicy",
]
