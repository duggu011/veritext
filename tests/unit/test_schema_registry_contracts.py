import pytest
from pydantic import ValidationError

from extractor.contracts import (
    ApprovedSchemaArtifact,
    ApprovedSchemaMetadata,
    CategoryDefinition,
    FieldDefinition,
    PlanningRefusal,
    SchemaCoverageEstimate,
    SchemaFitAssessment,
    SchemaSelection,
    SchemaSelectionPolicy,
    canonical_schema_hash,
)


def make_category(name: str = "Finding") -> CategoryDefinition:
    return CategoryDefinition(
        name=name,
        description="A source-backed finding.",
        fields=(
            FieldDefinition(
                name="summary",
                description="Short extracted source text.",
                value_type="text",
                required=True,
            ),
        ),
    )


def make_registry_metadata(
    *,
    categories: tuple[CategoryDefinition, ...],
    schema_id: str = "schema:generic-finding-v1",
    document_class: str = "generic_notice",
    domain_hints: tuple[str, ...] = ("generic",),
) -> ApprovedSchemaMetadata:
    return ApprovedSchemaMetadata(
        schema_id=schema_id,
        schema_version="1.0.0",
        schema_hash=canonical_schema_hash(
            approved_categories=categories,
            source_kind="schema_registry",
            schema_version="1.0.0",
            domain_hints=domain_hints,
            document_class=document_class,
        ),
        source_kind="schema_registry",
        domain_pack_id=None,
        document_class=document_class,
        created_from="schema_registry",
        refined_from_schema_id=None,
    )


def test_approved_schema_artifact_validates_hash_and_selection_metadata() -> None:
    categories = (make_category(),)
    artifact = ApprovedSchemaArtifact(
        schema_metadata=make_registry_metadata(categories=categories),
        approved_categories=categories,
        document_class="generic_notice",
        domain_hints=("generic",),
        match_basis=("document_class", "domain_hints"),
    )

    assert artifact.schema_metadata.source_kind == "schema_registry"
    assert artifact.schema_id == "schema:generic-finding-v1"
    assert artifact.domain_hints == ("generic",)

    bad_metadata = artifact.schema_metadata.model_copy(update={"schema_hash": "b" * 64})
    with pytest.raises(ValidationError, match="schema_metadata schema_hash must match"):
        ApprovedSchemaArtifact(
            schema_metadata=bad_metadata,
            approved_categories=categories,
            document_class="generic_notice",
            domain_hints=("generic",),
            match_basis=("document_class",),
        )

    with pytest.raises(ValidationError, match="document_class must match"):
        ApprovedSchemaArtifact(
            schema_metadata=artifact.schema_metadata,
            approved_categories=categories,
            document_class="other_notice",
            domain_hints=("generic",),
            match_basis=("document_class",),
        )


def test_schema_selection_policy_is_strict_and_threshold_bounded() -> None:
    policy = SchemaSelectionPolicy(
        require_approved_schema=True,
        minimum_schema_coverage=0.75,
        allow_planner_generated_fallback=False,
    )

    assert policy.require_approved_schema is True

    with pytest.raises(ValidationError):
        SchemaSelectionPolicy(
            require_approved_schema=True,
            minimum_schema_coverage=1.2,
            allow_planner_generated_fallback=False,
        )

    with pytest.raises(ValidationError):
        SchemaSelectionPolicy(
            require_approved_schema="yes",
            minimum_schema_coverage=0.75,
            allow_planner_generated_fallback=False,
        )


def test_schema_fit_assessment_requires_reason_codes_for_non_fit() -> None:
    coverage = SchemaCoverageEstimate(
        schema_id="schema:generic-finding-v1",
        category_name="Finding",
        coverage=0.8,
        rationale="The source supports the approved finding category.",
    )
    assessment = SchemaFitAssessment(
        schema_id="schema:generic-finding-v1",
        fits=True,
        overall_coverage=0.8,
        coverage_estimates=(coverage,),
        reason_codes=(),
    )

    assert assessment.fits is True

    with pytest.raises(ValidationError, match="non-fitting schema assessments require reason_codes"):
        SchemaFitAssessment(
            schema_id="schema:generic-finding-v1",
            fits=False,
            overall_coverage=0.2,
            coverage_estimates=(coverage,),
            reason_codes=(),
        )

    with pytest.raises(ValidationError, match="coverage estimate schema_id must match"):
        SchemaFitAssessment(
            schema_id="schema:generic-finding-v1",
            fits=False,
            overall_coverage=0.2,
            coverage_estimates=(
                coverage.model_copy(update={"schema_id": "schema:other"}),
            ),
            reason_codes=("coverage_below_threshold",),
        )


def test_schema_selection_requires_selected_schema_from_candidates() -> None:
    selection = SchemaSelection(
        document_class="generic_notice",
        domain_hints=("generic",),
        candidate_schema_ids=("schema:generic-finding-v1",),
        selected_schema_id="schema:generic-finding-v1",
        match_basis=("document_class",),
        selected_coverage=0.9,
        fit_assessments=(),
    )

    assert selection.selected_schema_id == "schema:generic-finding-v1"

    with pytest.raises(ValidationError, match="selected_schema_id must be one of candidate_schema_ids"):
        SchemaSelection(
            document_class="generic_notice",
            domain_hints=("generic",),
            candidate_schema_ids=("schema:generic-finding-v1",),
            selected_schema_id="schema:other",
            match_basis=("document_class",),
            selected_coverage=0.9,
            fit_assessments=(),
        )

    with pytest.raises(ValidationError, match="candidate_schema_ids must be unique"):
        SchemaSelection(
            document_class="generic_notice",
            domain_hints=("generic",),
            candidate_schema_ids=("schema:one", "schema:one"),
            selected_schema_id="schema:one",
            match_basis=("document_class",),
            selected_coverage=0.9,
            fit_assessments=(),
        )


def test_planning_refusal_requires_reasons_and_candidate_consistency() -> None:
    policy = SchemaSelectionPolicy(
        require_approved_schema=True,
        minimum_schema_coverage=0.75,
        allow_planner_generated_fallback=False,
    )
    assessment = SchemaFitAssessment(
        schema_id="schema:generic-finding-v1",
        fits=False,
        overall_coverage=0.2,
        coverage_estimates=(
            SchemaCoverageEstimate(
                schema_id="schema:generic-finding-v1",
                category_name="Finding",
                coverage=0.2,
                rationale="Only incidental support exists.",
            ),
        ),
        reason_codes=("coverage_below_threshold",),
    )
    refusal = PlanningRefusal(
        run_id="run-1",
        doc_id="doc-1",
        document_class="generic_notice",
        domain_hints=("generic",),
        policy=policy,
        candidate_schema_ids=("schema:generic-finding-v1",),
        fit_assessments=(assessment,),
        reason_codes=("coverage_below_threshold",),
    )

    assert refusal.reason_codes == ("coverage_below_threshold",)

    with pytest.raises(ValidationError):
        PlanningRefusal(
            run_id="run-1",
            doc_id="doc-1",
            document_class="generic_notice",
            domain_hints=("generic",),
            policy=policy,
            candidate_schema_ids=("schema:generic-finding-v1",),
            fit_assessments=(assessment,),
            reason_codes=(),
        )

    with pytest.raises(ValidationError, match="fit_assessment schema_id must be in candidate_schema_ids"):
        PlanningRefusal(
            run_id="run-1",
            doc_id="doc-1",
            document_class="generic_notice",
            domain_hints=("generic",),
            policy=policy,
            candidate_schema_ids=("schema:other",),
            fit_assessments=(assessment,),
            reason_codes=("coverage_below_threshold",),
        )
