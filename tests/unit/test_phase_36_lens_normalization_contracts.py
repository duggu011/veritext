import pytest
from pydantic import ValidationError

from extractor.contracts import (
    CategoryDefinition,
    Chunk,
    ChunkPolicy,
    CriticReport,
    DataPoint,
    ExtractionBudget,
    ExtractionPlan,
    FieldDefinition,
    FieldNormalizationPolicy,
    LensBudget,
    LensCandidate,
    LensDefinition,
    LensRegistry,
    NormalizationPolicy,
    NormalizationPolicyRegistry,
    SourceSpan,
    VerifierReport,
)
from extractor.contracts.lens_taxonomy import default_lens_registry
from extractor.executor.materialization import build_candidate
from extractor.executor.models import ExtractedCandidatePayload
from extractor.reconciler.materialization import build_reconciliation_result
from extractor.reconciler.models import ReconciliationBatch


def make_source_span(text: str = "appointed") -> SourceSpan:
    return SourceSpan(
        doc_id="doc-1",
        chunk_id="chunk-1",
        start_char=0,
        end_char=len(text),
        start_byte=0,
        end_byte=len(text.encode("utf-8")),
        text=text,
    )


def make_candidate_payload(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "candidate_id": "candidate-1",
        "run_id": "run-1",
        "doc_id": "doc-1",
        "chunk_id": "chunk-1",
        "lens": "event",
        "category": "PersonnelChange",
        "field_name": "change_type",
        "value": "appointment",
        "source_span": make_source_span().model_dump(mode="json"),
        "confidence": 0.8,
        "executor_call_id": "call-executor-1",
    }
    payload.update(updates)
    return payload


def make_plan() -> ExtractionPlan:
    category = CategoryDefinition(
        name="PersonnelChange",
        description="A source-backed personnel change.",
        fields=(
            FieldDefinition(
                name="change_type",
                description="The type of personnel change.",
                value_type="text",
                required=True,
            ),
        ),
    )
    return ExtractionPlan(
        run_id="run-1",
        doc_id="doc-1",
        domain_hints=("generic",),
        approved_categories=(category,),
        enabled_lenses=("event",),
        chunk_policy=ChunkPolicy(window_tokens=100, overlap_tokens=10),
        budget=ExtractionBudget(
            per_chunk_concurrency=1,
            lens_budgets=(LensBudget(lens="event", max_calls=1),),
        ),
    )


def make_chunk(text: str = "appointed") -> Chunk:
    text_bytes = text.encode("utf-8")
    return Chunk(
        chunk_id="chunk-1",
        doc_id="doc-1",
        chunk_index=0,
        text=text,
        start_char=0,
        end_char=len(text),
        start_byte=0,
        end_byte=len(text_bytes),
        start_token=0,
        end_token=1,
    )


def make_data_point_payload(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "data_point_id": "datapoint-1",
        "run_id": "run-1",
        "doc_id": "doc-1",
        "category": "PersonnelChange",
        "field_name": "change_type",
        "value": "appointment",
        "source_span": make_source_span().model_dump(mode="json"),
        "confidence": 0.8,
        "contributing_candidate_ids": ("candidate-1",),
        "critic_report_ids": ("critic-1",),
        "verifier_report_ids": ("verifier-1",),
        "reconciliation_decision_id": "reconcile-1",
    }
    payload.update(updates)
    return payload


def test_default_lens_registry_separates_executable_and_contract_only_roles() -> None:
    registry = default_lens_registry()

    assert registry.definition_for("entity").runtime_status == "executable"
    assert registry.definition_for("definition").runtime_status == "contract_only"
    assert registry.executable_names == ("entity", "event", "claim", "number")
    assert "quantity_with_unit" in registry.contract_only_names

    with pytest.raises(ValidationError, match="planned-only lens cannot be executable"):
        LensDefinition(
            name="definition",
            runtime_status="executable",
            description="Defined terms in source text.",
            source_requirements=("exact source span",),
            allowed_value_kinds=("text",),
        )


def test_lens_registry_rejects_duplicate_roles() -> None:
    entity = LensDefinition(
        name="entity",
        runtime_status="executable",
        description="Named source-backed entities.",
        source_requirements=("exact source span",),
        allowed_value_kinds=("entity",),
    )

    with pytest.raises(ValidationError, match="lens definitions must be unique"):
        LensRegistry(definitions=(entity, entity))


def test_normalization_policy_registry_validates_unique_policy_versions() -> None:
    policy = NormalizationPolicy(
        policy_id="source-traced-label",
        version="1",
        mode="source_traced_label",
        input_kind="text",
        output_kind="text",
        description="Derive a canonical label from a source-backed phrase.",
    )
    field_policy = FieldNormalizationPolicy(
        category_name="PersonnelChange",
        field_name="change_type",
        value_kind="text",
        policy_id="source-traced-label",
        reject_unsupported=True,
    )

    registry = NormalizationPolicyRegistry(policies=(policy,))

    assert registry.policy_ids == ("source-traced-label@1",)
    assert field_policy.reject_unsupported is True

    with pytest.raises(ValidationError, match="normalization policies must be unique"):
        NormalizationPolicyRegistry(policies=(policy, policy))


def test_candidate_and_data_point_read_legacy_payloads_without_normalization_fields() -> None:
    candidate = LensCandidate.model_validate(make_candidate_payload())
    data_point = DataPoint.model_validate(make_data_point_payload())

    assert candidate.value == "appointment"
    assert candidate.value_verbatim is None
    assert candidate.value_canonical is None
    assert candidate.value_kind == "text"
    assert candidate.normalization_status == "not_normalized"
    assert data_point.value_verbatim is None
    assert data_point.normalization_status == "not_normalized"


def test_candidate_and_data_point_validate_canonicalization_metadata() -> None:
    normalized_fields = {
        "value_verbatim": "appointed",
        "value_canonical": "appointment",
        "value_kind": "text",
        "normalization_status": "canonicalized",
        "normalization_policy_id": "source-traced-label",
        "normalization_policy_version": "1",
    }

    candidate = LensCandidate.model_validate(
        make_candidate_payload(**normalized_fields)
    )
    data_point = DataPoint.model_validate(
        make_data_point_payload(**normalized_fields)
    )

    assert candidate.value == "appointment"
    assert candidate.value_verbatim == "appointed"
    assert candidate.value_canonical == "appointment"
    assert data_point.value_canonical == "appointment"

    invalid = dict(normalized_fields)
    invalid.pop("normalization_policy_id")
    with pytest.raises(ValidationError, match="canonicalized normalization requires"):
        LensCandidate.model_validate(make_candidate_payload(**invalid))


def test_extraction_plan_rejects_contract_only_lens_execution() -> None:
    category = CategoryDefinition(
        name="Finding",
        description="A source-backed finding.",
        fields=(
            FieldDefinition(
                name="summary",
                description="Short extracted value.",
                value_type="text",
                required=True,
            ),
        ),
    )

    with pytest.raises(ValidationError):
        ExtractionPlan(
            run_id="run-1",
            doc_id="doc-1",
            domain_hints=("generic",),
            approved_categories=(category,),
            enabled_lenses=("definition",),
            chunk_policy=ChunkPolicy(window_tokens=100, overlap_tokens=10),
            budget=ExtractionBudget(
                per_chunk_concurrency=1,
                lens_budgets=(LensBudget(lens="definition", max_calls=1),),
            ),
        )


def test_build_candidate_populates_verbatim_and_canonical_metadata() -> None:
    candidate = build_candidate(
        plan=make_plan(),
        lens="event",
        chunk=make_chunk(),
        payload=ExtractedCandidatePayload(
            category="PersonnelChange",
            field_name="change_type",
            value="appointment",
            source_length=len("appointed"),
            start_char=0,
            confidence=0.8,
        ),
        start_char=0,
        source_text="appointed",
        candidate_index=0,
        executor_call_id="call-executor-1",
    )

    assert candidate.value == "appointment"
    assert candidate.value_verbatim == "appointed"
    assert candidate.value_canonical == "appointment"
    assert candidate.normalization_status == "canonicalized"
    assert candidate.normalization_policy_id == "source-traced-label"


def test_reconciler_carries_source_candidate_normalization_metadata() -> None:
    candidate = LensCandidate.model_validate(
        make_candidate_payload(
            value_verbatim="appointed",
            value_canonical="appointment",
            value_kind="text",
            normalization_status="canonicalized",
            normalization_policy_id="source-traced-label",
            normalization_policy_version="1",
        )
    )
    critic = CriticReport(
        report_id="critic-1",
        run_id="run-1",
        candidate_id=candidate.candidate_id,
        critic_call_id="call-critic-1",
        plausibility_score=0.9,
        accepted=True,
        issues=(),
    )
    verifier = VerifierReport(
        report_id="verifier-1",
        run_id="run-1",
        candidate_id=candidate.candidate_id,
        verifier_call_id="call-verifier-1",
        span_verified=True,
        category_verified=True,
        alignment_score=0.85,
        accepted=True,
        rejection_reasons=(),
    )

    data_points, rejections = build_reconciliation_result(
        plan=make_plan(),
        candidates_by_id={candidate.candidate_id: candidate},
        critic_reports_by_candidate_id={candidate.candidate_id: critic},
        verifier_reports_by_candidate_id={candidate.candidate_id: verifier},
        batch=ReconciliationBatch(
            groups=((candidate.candidate_id, (candidate.candidate_id,)),),
            rejected=(),
        ),
    )

    assert rejections == ()
    assert data_points[0].value == "appointment"
    assert data_points[0].value_verbatim == "appointed"
    assert data_points[0].value_canonical == "appointment"
    assert data_points[0].normalization_policy_id == "source-traced-label"
