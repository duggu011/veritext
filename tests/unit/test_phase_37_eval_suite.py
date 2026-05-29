from pathlib import Path

from extractor.evals.suites import evaluate_suite_manifest, load_suite_manifest


ROOT = Path(__file__).resolve().parents[2]
SUITE_PATH = ROOT / "evals" / "suites" / "phase_37_expanded_lenses_round_1.json"


def test_phase_37_expanded_lenses_suite_scores_source_role_fixture() -> None:
    manifest = load_suite_manifest(SUITE_PATH, repo_root=ROOT)

    assert [fixture.fixture_id for fixture in manifest.fixtures] == [
        "phase_37_lens_roles"
    ]

    result = evaluate_suite_manifest(SUITE_PATH, repo_root=ROOT)

    assert result.passed is True
    assert result.suite_id == "phase_37_expanded_lenses_round_1"
    assert result.metrics.expected_count == 4
    assert result.metrics.actual_count == 4
    assert result.metrics.precision == 1.0
    assert result.metrics.recall == 1.0
    assert result.metrics.f1 == 1.0
    assert result.metrics.provenance_recall == 1.0
    assert result.metrics.invariant_violation_count == 0
    assert result.threshold_failures == ()

    assert {
        breakdown.category for breakdown in result.category_metrics
    } == {
        "DefinedTerm",
        "QuantityWithUnit",
        "SourceCitation",
        "TemporalRequirement",
    }
    assert {
        (breakdown.category, breakdown.field_name)
        for breakdown in result.field_metrics
    } == {
        ("DefinedTerm", "definition_text"),
        ("QuantityWithUnit", "quantity_text"),
        ("SourceCitation", "reference_text"),
        ("TemporalRequirement", "time_window"),
    }
