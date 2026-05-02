from pathlib import Path

from extractor.llm import PromptLoader


ROOT = Path(__file__).resolve().parents[2]


def _prompt_bodies() -> dict[str, str]:
    return {prompt.stage: prompt.body for prompt in PromptLoader(ROOT / "prompts").load_all()}


def test_planner_prompts_require_document_semantic_roles() -> None:
    prompts = _prompt_bodies()
    propose = prompts["planner.propose_schema"]
    critique = prompts["planner.critique_schema"]

    for phrase in (
        "Semantic-role coverage:",
        "Event-like facts should preserve",
        "Metric facts should preserve",
        "Guidance facts should preserve",
        "Personnel facts should preserve",
        "Regulatory or rate-change facts should preserve",
        "guidance value/range",
        "provenance-ready evidence",
    ):
        assert phrase in propose

    for phrase in (
        "source-grounded but too coarse",
        "main atomic facts with exact provenance",
        "For event-like facts",
        "For metric facts",
        "For guidance, risk, personnel, and regulatory facts",
        "semantic label",
    ):
        assert phrase in critique


def test_planner_prompts_require_naming_stability_without_closed_ontology() -> None:
    prompts = _prompt_bodies()
    propose = prompts["planner.propose_schema"]
    critique = prompts["planner.critique_schema"]

    for body in (propose, critique):
        for phrase in (
            "Naming-stability pass:",
            "not a closed ontology",
            "section headings",
            "conventional reusable name",
            "source-backed distinction",
            "ForwardGuidance",
            "RegulatoryRisk",
            "change_pct",
            "exposure_pct",
            "event_date",
            "guidance_value",
            "facility_contribution",
        ):
            assert phrase in body


def test_planner_prompts_prevent_over_specific_schema_descriptions() -> None:
    prompts = _prompt_bodies()
    propose = prompts["planner.propose_schema"]
    critique = prompts["planner.critique_schema"]

    for phrase in (
        "Category descriptions for reusable categories must define the source-backed fact class",
        "CorporateEvent covers source-backed significant business or corporate events",
        "do not reserve CorporateEvent for one named transaction",
        "Include an optional OperationalMetric.facility field",
        "Do not move that facility role to CorporateEvent",
        "When the field name is facility, describe it as the bare source-stated facility or asset name",
        "Do not require location unless the field name or source role explicitly requires facility plus location",
        "For fields ending in _type",
        "Noun-form normalization is valid",
    ):
        assert phrase in propose

    for phrase in (
        "Correct reusable category descriptions that reserve category semantics for one source example",
        "do not approve a CorporateEvent description that makes one named transaction the category's exclusive scope",
        "Require an optional OperationalMetric.facility field",
        "moves the facility role only to CorporateEvent",
        "Correct facility field descriptions that require name plus location when the field is simply facility",
        "A bare source-stated facility or asset name is valid",
        "Correct descriptions for fields ending in _type",
        "source-traced concise labels",
    ):
        assert phrase in critique


def test_planner_prompts_reject_generic_role_collapse() -> None:
    prompts = _prompt_bodies()
    propose = prompts["planner.propose_schema"]
    critique = prompts["planner.critique_schema"]

    for body in (propose, critique):
        for phrase in (
            "role collapse",
            "deadline",
            "effective_date",
            "value",
            "rate",
            "party",
            "person",
            "summary",
            "event type",
            "prior_rate",
            "new_rate",
            "expected_close_date",
            "forecast_value",
            "guidance_value",
            "change_type",
        ):
            assert phrase in body


def test_planner_prompts_require_forward_guidance_relation_names() -> None:
    prompts = _prompt_bodies()
    propose = prompts["planner.propose_schema"]
    critique = prompts["planner.critique_schema"]

    for body in (propose, critique):
        for phrase in (
            "Use speaker for the person or organization that states, reaffirms, or updates guidance",
            "not generic person, party, or role",
            "Use target_date for a by-date, deadline, or target-achievement date",
            "not generic period",
            "Use condition for one stated contingency, caveat, threshold, or dependency",
            "conditions only when the source states multiple independent conditions",
        ):
            assert phrase in body


def test_planner_prompts_require_metric_notable_qualifier_name() -> None:
    prompts = _prompt_bodies()
    propose = prompts["planner.propose_schema"]
    critique = prompts["planner.critique_schema"]

    for body in (propose, critique):
        for phrase in (
            "Use notable_qualifier for source-stated metric qualifiers",
            "first time in N periods",
            "do not hide that qualifier in summary",
        ):
            assert phrase in body


def test_planner_critique_rejects_synonym_drift_but_allows_new_roles() -> None:
    prompts = _prompt_bodies()
    critique = prompts["planner.critique_schema"]

    for phrase in (
        "Reject avoidable category synonym drift",
        "Reject avoidable field synonym drift",
        "Guidance when the source role is forward-looking company guidance",
        "RegulatoryRateChange when the source role is regulatory risk or exposure",
        "change_percentage when change_pct fits",
        "forecast_value inside forward guidance when guidance_value fits",
        "Do not reject merely because a schema uses a new name",
        "new name is a synonym for a stable reusable role",
    ):
        assert phrase in critique


def test_executor_prompts_require_provenance_for_field_meaning() -> None:
    prompts = _prompt_bodies()
    executor_bodies = [
        prompts["executor.entity"],
        prompts["executor.event"],
        prompts["executor.claim"],
        prompts["executor.number"],
    ]

    for body in executor_bodies:
        assert "supports both" in body
        assert "field meaning" in body

    combined = "\n".join(executor_bodies)
    for phrase in (
        "$88.0 million forecast",
        "19.5% margin",
        "from 15.0%",
        "to 26.5%",
        "CEO Marcus Bell",
        "appointed Chief Sustainability Officer",
        "event_type",
        "change_type",
        ):
            assert phrase in combined


def test_executor_prompts_require_atomic_value_boundary_discipline() -> None:
    prompts = _prompt_bodies()
    number = prompts["executor.number"]
    entity = prompts["executor.entity"]
    combined = "\n".join((number, entity))

    for phrase in (
        "For atomic numeric fields such as forecast_value, target_value, margin, amount, rate, prior_rate, or new_rate",
        "do not include role labels such as forecast, target, margin, value, amount, rate, prior, or new when the field name already carries that role",
        "Reject role-label contamination such as selecting \"$88.0 million forecast\" for forecast_value",
        "Reject role-label contamination such as selecting \"29.0% target\" for target_value",
        "For bare-entity fields such as facility, party, person, organization, asset, or issuing_authority",
        "do not append location, role, date, action, or descriptive qualifiers unless the approved field explicitly bundles them",
        "For metric_name and other label fields, select the source words that name the metric or label, not surrounding period or value words",
    ):
        assert phrase in combined


def test_executor_prompts_allow_source_traced_label_normalization() -> None:
    prompts = _prompt_bodies()
    event = prompts["executor.event"]
    claim = prompts["executor.claim"]

    for body in (event, claim):
        for phrase in (
            "For label fields such as event_type, change_type, exposure_type, risk_type, or metric_name",
            "value may use a concise noun-form label when every content word traces to the selected source phrase",
            "keep the source span over the source words, not the normalized label",
            "Noun-form normalization such as appointed to appointment is valid",
        ):
            assert phrase in body


def test_executor_prompts_require_statement_clause_span_widths() -> None:
    prompts = _prompt_bodies()
    claim = prompts["executor.claim"]
    event = prompts["executor.event"]

    for body in (claim, event):
        for phrase in (
            "For statement-like fields such as summary, statement, description, or condition",
            "choose the full source sentence or standalone clause with closing punctuation",
            "set value equal to that span verbatim",
            "For qualifier or attribute fields such as notable_qualifier or asset_detail",
            "choose the shortest exact phrase or clause that carries the qualifier/detail role",
            "Do not trim leading dates, prices, values, conditions, or sentence punctuation from statement-like fields",
        ):
            assert phrase in body
