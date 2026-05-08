from __future__ import annotations

from dataclasses import dataclass

from extractor.contracts import (
    ApprovedSchemaArtifact,
    Document,
    PlanningRefusal,
    PlanningRefusalReasonCode,
    SchemaCoverageEstimate,
    SchemaFitAssessment,
    SchemaSelection,
    SchemaSelectionPolicy,
)
from extractor.planner.models import DocumentClassification
from extractor.planner.schema_registry import select_schema_registry_candidates


DEFAULT_SCHEMA_SELECTION_POLICY = SchemaSelectionPolicy(
    require_approved_schema=False,
    minimum_schema_coverage=0.0,
    allow_planner_generated_fallback=True,
)


@dataclass(frozen=True)
class SchemaFitDecision:
    selected_schema: ApprovedSchemaArtifact | None
    selection: SchemaSelection
    refusal: PlanningRefusal | None


def decide_schema_fit(
    *,
    run_id: str,
    document: Document,
    classification: DocumentClassification,
    domain_hints: tuple[str, ...],
    approved_schema_artifacts: tuple[ApprovedSchemaArtifact, ...],
    policy: SchemaSelectionPolicy,
) -> SchemaFitDecision:
    candidates = select_schema_registry_candidates(
        approved_schema_artifacts,
        document_class=classification.document_type,
        domain_hints=domain_hints,
    )
    assessments = tuple(
        _assess_schema_fit(
            artifact,
            classification=classification,
            policy=policy,
        )
        for artifact in candidates
    )
    fitting_candidates = tuple(
        (artifact, assessment)
        for artifact, assessment in zip(candidates, assessments, strict=True)
        if assessment.fits
    )

    selected_schema: ApprovedSchemaArtifact | None = None
    selected_coverage: float | None = None
    if len(fitting_candidates) == 1:
        selected_schema = fitting_candidates[0][0]
        selected_coverage = fitting_candidates[0][1].overall_coverage

    selection = SchemaSelection(
        document_class=classification.document_type,
        domain_hints=domain_hints,
        candidate_schema_ids=tuple(artifact.schema_id for artifact in candidates),
        selected_schema_id=selected_schema.schema_id if selected_schema is not None else None,
        match_basis=_selection_match_basis(candidates),
        selected_coverage=selected_coverage,
        fit_assessments=assessments,
    )
    if selected_schema is not None:
        return SchemaFitDecision(
            selected_schema=selected_schema,
            selection=selection,
            refusal=None,
        )
    if policy.allow_planner_generated_fallback:
        return SchemaFitDecision(
            selected_schema=None,
            selection=selection,
            refusal=None,
        )

    reason_codes = _selection_refusal_reasons(
        classification=classification,
        candidates=candidates,
        fitting_count=len(fitting_candidates),
        assessments=assessments,
    )
    refusal = PlanningRefusal(
        run_id=run_id,
        doc_id=document.doc_id,
        document_class=classification.document_type,
        domain_hints=domain_hints,
        policy=policy,
        candidate_schema_ids=selection.candidate_schema_ids,
        fit_assessments=assessments,
        reason_codes=reason_codes,
    )
    return SchemaFitDecision(
        selected_schema=None,
        selection=selection,
        refusal=refusal,
    )


def _assess_schema_fit(
    artifact: ApprovedSchemaArtifact,
    *,
    classification: DocumentClassification,
    policy: SchemaSelectionPolicy,
) -> SchemaFitAssessment:
    # Phase 27 keeps fit assessment deterministic until a human-filled prompt
    # is approved. Classification confidence is the auditable fit proxy.
    coverage = classification.confidence
    reason_codes: tuple[PlanningRefusalReasonCode, ...] = ()
    fits = coverage >= policy.minimum_schema_coverage
    if not fits:
        reason_codes = ("coverage_below_threshold",)

    estimates = tuple(
        SchemaCoverageEstimate(
            schema_id=artifact.schema_id,
            category_name=category.name,
            coverage=coverage,
            rationale=(
                "Schema fit uses the planner document-class confidence as a "
                "deterministic coverage proxy for the approved category."
            ),
        )
        for category in artifact.approved_categories
    )
    return SchemaFitAssessment(
        schema_id=artifact.schema_id,
        fits=fits,
        overall_coverage=coverage,
        coverage_estimates=estimates,
        reason_codes=reason_codes,
    )


def _selection_match_basis(candidates: tuple[ApprovedSchemaArtifact, ...]) -> tuple[str, ...]:
    basis: list[str] = []
    for candidate in candidates:
        for entry in candidate.match_basis:
            if entry not in basis:
                basis.append(entry)
    if not basis:
        basis.extend(("document_class", "domain_hints"))
    return tuple(basis)


def _selection_refusal_reasons(
    *,
    classification: DocumentClassification,
    candidates: tuple[ApprovedSchemaArtifact, ...],
    fitting_count: int,
    assessments: tuple[SchemaFitAssessment, ...],
) -> tuple[PlanningRefusalReasonCode, ...]:
    if not candidates:
        if classification.document_type == "unknown_document":
            return ("document_out_of_scope",)
        return ("no_approved_schema_candidates",)
    if fitting_count > 1:
        return ("ambiguous_schema_candidates",)

    reason_codes: list[PlanningRefusalReasonCode] = []
    for assessment in assessments:
        for reason_code in assessment.reason_codes:
            if reason_code not in reason_codes:
                reason_codes.append(reason_code)
    if reason_codes:
        return tuple(reason_codes)
    return ("coverage_below_threshold",)


__all__ = [
    "DEFAULT_SCHEMA_SELECTION_POLICY",
    "SchemaFitDecision",
    "decide_schema_fit",
]
