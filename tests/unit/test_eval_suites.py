import copy
import importlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from extractor.evals import EvaluationError
from extractor.evals.cli import main as eval_main


ROOT = Path(__file__).resolve().parents[2]


def _suites_module():
    try:
        return importlib.import_module("extractor.evals.suites")
    except ModuleNotFoundError:
        pytest.fail("extractor.evals.suites must provide suite manifest loading")


def _strict_thresholds() -> dict[str, Any]:
    return {
        "max_invariant_violations": 0,
        "min_f1": 1.0,
        "min_precision": 1.0,
        "min_provenance_recall": 1.0,
        "min_recall": 1.0,
    }


def _valid_manifest() -> dict[str, Any]:
    return {
        "suite_id": "unit_suite",
        "description": "Unit-test manifest for suite loader validation.",
        "fixtures": [
            {
                "fixture_id": "minimal_financial_update",
                "case_path": "evals/fixtures/minimal_financial_update/expected.json",
                "report_path": "evals/fixtures/minimal_financial_update/report.example.json",
            }
        ],
        "thresholds": {
            "global": _strict_thresholds(),
            "categories": [
                {
                    "category": "FinancialMetric",
                    "thresholds": _strict_thresholds(),
                }
            ],
            "fields": [
                {
                    "category": "FinancialMetric",
                    "field_name": "statement",
                    "thresholds": _strict_thresholds(),
                }
            ],
        },
    }


def _write_manifest(tmp_path: Path, payload: dict[str, Any]) -> Path:
    manifest_path = tmp_path / "suite.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    return manifest_path


def _loose_thresholds() -> dict[str, Any]:
    return {
        "max_invariant_violations": 0,
        "min_f1": 0.0,
        "min_precision": 0.0,
        "min_provenance_recall": 0.0,
        "min_recall": 0.0,
    }


def _copy_fixture_repo(tmp_path: Path, fixture_id: str) -> Path:
    repo_root = tmp_path / "repo"
    fixture_dir = repo_root / "evals" / "fixtures" / fixture_id
    fixture_dir.parent.mkdir(parents=True)
    shutil.copytree(ROOT / "evals" / "fixtures" / fixture_id, fixture_dir)
    return repo_root


def test_load_suite_manifest_accepts_valid_manifest(tmp_path: Path) -> None:
    suites = _suites_module()
    manifest = suites.load_suite_manifest(
        _write_manifest(tmp_path, _valid_manifest()),
        repo_root=ROOT,
    )

    assert manifest.suite_id == "unit_suite"
    assert manifest.fixtures[0].fixture_id == "minimal_financial_update"
    assert (
        manifest.fixtures[0].case_path
        == "evals/fixtures/minimal_financial_update/expected.json"
    )
    assert manifest.thresholds.global_thresholds.min_f1 == 1.0
    assert manifest.thresholds.categories[0].category == "FinancialMetric"
    assert manifest.thresholds.fields[0].field_name == "statement"


def test_load_suite_manifest_rejects_duplicate_fixture_ids(tmp_path: Path) -> None:
    suites = _suites_module()
    payload = _valid_manifest()
    payload["fixtures"].append(copy.deepcopy(payload["fixtures"][0]))

    with pytest.raises(EvaluationError, match="duplicate suite fixture IDs"):
        suites.load_suite_manifest(_write_manifest(tmp_path, payload), repo_root=ROOT)


def test_load_suite_manifest_rejects_bad_fixture_paths(tmp_path: Path) -> None:
    suites = _suites_module()
    payload = _valid_manifest()
    payload["fixtures"][0]["case_path"] = "../outside.json"

    with pytest.raises(EvaluationError, match="case_path must be repo-relative"):
        suites.load_suite_manifest(_write_manifest(tmp_path, payload), repo_root=ROOT)

    payload = _valid_manifest()
    payload["fixtures"][0]["report_path"] = (
        "evals/fixtures/minimal_financial_update/missing-report.json"
    )

    with pytest.raises(EvaluationError, match="report_path does not exist"):
        suites.load_suite_manifest(_write_manifest(tmp_path, payload), repo_root=ROOT)


def test_load_suite_manifest_rejects_duplicate_threshold_keys(tmp_path: Path) -> None:
    suites = _suites_module()
    payload = _valid_manifest()
    thresholds = payload["thresholds"]
    thresholds["categories"].append(copy.deepcopy(thresholds["categories"][0]))

    with pytest.raises(EvaluationError, match="duplicate category threshold keys"):
        suites.load_suite_manifest(_write_manifest(tmp_path, payload), repo_root=ROOT)

    payload = _valid_manifest()
    thresholds = payload["thresholds"]
    thresholds["fields"].append(copy.deepcopy(thresholds["fields"][0]))

    with pytest.raises(EvaluationError, match="duplicate field threshold keys"):
        suites.load_suite_manifest(_write_manifest(tmp_path, payload), repo_root=ROOT)


def test_load_suite_manifest_rejects_invalid_thresholds(tmp_path: Path) -> None:
    suites = _suites_module()
    payload = _valid_manifest()
    payload["thresholds"]["global"]["min_precision"] = 1.01

    with pytest.raises(EvaluationError, match="Invalid evaluation suite manifest"):
        suites.load_suite_manifest(_write_manifest(tmp_path, payload), repo_root=ROOT)


def test_load_suite_manifest_requires_invariant_allowance_rationale(
    tmp_path: Path,
) -> None:
    suites = _suites_module()
    payload = _valid_manifest()
    payload["thresholds"]["global"]["max_invariant_violations"] = 1

    with pytest.raises(
        EvaluationError,
        match="non-zero invariant allowance requires rationale",
    ):
        suites.load_suite_manifest(_write_manifest(tmp_path, payload), repo_root=ROOT)

    payload["thresholds"]["global"]["invariant_allowance_rationale"] = (
        "Synthetic broken fixture used to verify invariant reporting."
    )
    manifest = suites.load_suite_manifest(
        _write_manifest(tmp_path, payload),
        repo_root=ROOT,
    )

    assert manifest.thresholds.global_thresholds.max_invariant_violations == 1


def test_phase_29_core_suite_manifest_loads_static_checked_in_reports() -> None:
    suites = _suites_module()

    manifest = suites.load_suite_manifest(
        ROOT / "evals" / "suites" / "phase_29_core.json",
        repo_root=ROOT,
    )

    assert [fixture.fixture_id for fixture in manifest.fixtures] == [
        "minimal_financial_update",
        "minimal_contract_obligation",
        "minimal_policy_controls",
        "hard_mixed_distractors",
        "legal_contracts_core",
    ]
    assert all(
        fixture.report_path.endswith("report.example.json")
        for fixture in manifest.fixtures
    )
    assert "medium_research_brief" not in {
        fixture.fixture_id for fixture in manifest.fixtures
    }


def test_phase_30_diverse_corpus_suite_skeleton_scores_and_covers_thresholds() -> None:
    suites = _suites_module()
    manifest_path = ROOT / "evals" / "suites" / "phase_30_diverse_corpus_round_1.json"

    manifest = suites.load_suite_manifest(manifest_path, repo_root=ROOT)
    fixture_ids = {fixture.fixture_id for fixture in manifest.fixtures}
    assert "legal_contracts_core" in fixture_ids
    assert all(
        fixture.report_path.endswith("report.example.json")
        for fixture in manifest.fixtures
    )
    assert manifest.thresholds.global_thresholds.min_precision == 1.0
    assert manifest.thresholds.global_thresholds.min_recall == 1.0
    assert manifest.thresholds.global_thresholds.min_f1 == 1.0
    assert manifest.thresholds.global_thresholds.min_provenance_recall == 1.0
    assert manifest.thresholds.global_thresholds.max_invariant_violations == 0

    result = suites.evaluate_suite_manifest(manifest_path, repo_root=ROOT)

    assert result.passed is True
    assert result.suite_id == "phase_30_diverse_corpus_round_1"
    assert result.metrics.precision == 1.0
    assert result.metrics.recall == 1.0
    assert result.metrics.f1 == 1.0
    assert result.metrics.provenance_recall == 1.0
    assert result.metrics.invariant_violation_count == 0
    assert result.threshold_failures == ()

    threshold_categories = {
        threshold.category for threshold in manifest.thresholds.categories
    }
    result_categories = {
        breakdown.category for breakdown in result.category_metrics
    }
    assert result_categories <= threshold_categories

    threshold_fields = {
        (threshold.category, threshold.field_name)
        for threshold in manifest.thresholds.fields
    }
    result_fields = {
        (breakdown.category, breakdown.field_name)
        for breakdown in result.field_metrics
    }
    assert result_fields <= threshold_fields


def test_evaluate_suite_manifest_scores_static_core_suite() -> None:
    suites = _suites_module()

    result = suites.evaluate_suite_manifest(
        ROOT / "evals" / "suites" / "phase_29_core.json",
        repo_root=ROOT,
    )

    assert result.passed is True
    assert result.suite_id == "phase_29_core"
    assert result.metrics.expected_count == 21
    assert result.metrics.actual_count == 21
    assert result.metrics.precision == 1.0
    assert result.metrics.recall == 1.0
    assert result.metrics.f1 == 1.0
    assert result.metrics.provenance_recall == 1.0
    assert result.metrics.invariant_violation_count == 0
    assert result.threshold_failures == ()
    assert [fixture.fixture_id for fixture in result.fixtures] == [
        "minimal_financial_update",
        "minimal_contract_obligation",
        "minimal_policy_controls",
        "hard_mixed_distractors",
        "legal_contracts_core",
    ]


def test_evaluate_suite_manifest_reports_field_threshold_failures(
    tmp_path: Path,
) -> None:
    suites = _suites_module()
    repo_root = _copy_fixture_repo(tmp_path, "minimal_financial_update")
    fixture_dir = repo_root / "evals" / "fixtures" / "minimal_financial_update"

    case_payload = json.loads(
        (fixture_dir / "expected.json").read_text(encoding="utf-8")
    )
    case_payload["thresholds"] = _loose_thresholds()
    (fixture_dir / "expected.json").write_text(json.dumps(case_payload), encoding="utf-8")

    report_path = fixture_dir / "report.example.json"
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    report_payload["data_points"] = report_payload["data_points"][1:]
    report_payload["output_data_point_ids"] = [
        point["data_point_id"] for point in report_payload["data_points"]
    ]
    report_path.write_text(json.dumps(report_payload), encoding="utf-8")

    payload = _valid_manifest()
    payload["fixtures"][0] = {
        "fixture_id": "minimal_financial_update",
        "case_path": "evals/fixtures/minimal_financial_update/expected.json",
        "report_path": "evals/fixtures/minimal_financial_update/report.example.json",
    }
    payload["thresholds"] = {
        "global": _loose_thresholds(),
        "fields": [
            {
                "category": "FinancialMetric",
                "field_name": "statement",
                "thresholds": {
                    **_loose_thresholds(),
                    "min_recall": 1.0,
                },
            }
        ],
    }

    result = suites.evaluate_suite_manifest(
        _write_manifest(tmp_path, payload),
        repo_root=repo_root,
    )

    assert result.passed is False
    assert result.metrics.recall == pytest.approx(2 / 3)
    assert len(result.threshold_failures) == 1
    failure = result.threshold_failures[0]
    assert failure.suite_id == "unit_suite"
    assert failure.scope == "field"
    assert failure.category == "FinancialMetric"
    assert failure.field_name == "statement"
    assert failure.metric == "recall"
    assert failure.actual == pytest.approx(1 / 2)
    assert failure.threshold == 1.0


def test_eval_cli_scores_suite_manifest(capsys: pytest.CaptureFixture[str]) -> None:
    status = eval_main(
        ("--suite", str(ROOT / "evals" / "suites" / "phase_29_core.json"))
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert status == 0
    assert payload["passed"] is True
    assert payload["suite_id"] == "phase_29_core"
    assert payload["metrics"]["expected_count"] == 21
    assert len(payload["fixtures"]) == 5
    assert payload["threshold_failures"] == []
