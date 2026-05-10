import copy
import importlib
import json
from pathlib import Path
from typing import Any

import pytest

from extractor.evals import EvaluationError


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
