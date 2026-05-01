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
