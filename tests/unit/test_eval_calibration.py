import copy
import json
import shutil
from pathlib import Path

import pytest

from extractor.evals.cli import main as eval_main


ROOT = Path(__file__).resolve().parents[2]


def _copy_fixture_repo(tmp_path: Path, fixture_id: str) -> Path:
    repo_root = tmp_path / "repo"
    fixture_dir = repo_root / "evals" / "fixtures" / fixture_id
    fixture_dir.parent.mkdir(parents=True)
    shutil.copytree(ROOT / "evals" / "fixtures" / fixture_id, fixture_dir)
    return repo_root


def test_calibration_report_bins_phase_30_suite_deterministically() -> None:
    from extractor.evals.calibration import (
        DEFAULT_CALIBRATION_BINS,
        generate_calibration_report,
    )

    suite_path = ROOT / "evals" / "suites" / "phase_30_diverse_corpus_round_1.json"
    report = generate_calibration_report(suite_path, repo_root=ROOT)
    second_report = generate_calibration_report(suite_path, repo_root=ROOT)

    assert report == second_report
    assert report.passed is True
    assert report.suite_id == "phase_30_diverse_corpus_round_1"
    assert report.total_data_points == 49
    assert report.matched_data_points == 49
    assert report.unmatched_data_points == 0
    assert tuple(
        (bin.lower_bound, bin.upper_bound, bin.includes_upper_bound)
        for bin in report.bins
    ) == DEFAULT_CALIBRATION_BINS
    assert sum(bin.count for bin in report.bins) == 49
    assert report.empty_bin_indexes
    assert report.expected_calibration_error > 0.0
    assert report.expected_calibration_error == report.provenance_calibration_error
    assert all(
        bin.count == 0 or bin.exact_match_accuracy == 1.0 for bin in report.bins
    )
    assert all(
        bin.count == 0 or bin.exact_provenance_accuracy == 1.0
        for bin in report.bins
    )


def test_calibration_report_counts_unmatched_actual_points(tmp_path: Path) -> None:
    from extractor.evals.calibration import generate_calibration_report

    repo_root = _copy_fixture_repo(tmp_path, "minimal_financial_update")
    fixture_dir = repo_root / "evals" / "fixtures" / "minimal_financial_update"
    report_path = fixture_dir / "report.example.json"
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    unexpected = copy.deepcopy(report_payload["data_points"][0])
    unexpected["data_point_id"] = "dp-unexpected"
    unexpected["category"] = "Unexpected"
    report_payload["data_points"][0] = unexpected
    report_payload["output_data_point_ids"] = [
        point["data_point_id"] for point in report_payload["data_points"]
    ]
    report_path.write_text(json.dumps(report_payload), encoding="utf-8")

    suite_payload = {
        "suite_id": "unit_calibration_suite",
        "description": "Unit calibration suite with one unmatched actual point.",
        "fixtures": [
            {
                "fixture_id": "minimal_financial_update",
                "case_path": "evals/fixtures/minimal_financial_update/expected.json",
                "report_path": "evals/fixtures/minimal_financial_update/report.example.json",
            }
        ],
    }
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(json.dumps(suite_payload), encoding="utf-8")

    report = generate_calibration_report(suite_path, repo_root=repo_root)

    assert report.total_data_points == 3
    assert report.matched_data_points == 2
    assert report.unmatched_data_points == 1
    bin_90_95 = next(bin for bin in report.bins if bin.lower_bound == 0.9)
    final_bin = next(bin for bin in report.bins if bin.lower_bound == 0.95)
    assert bin_90_95.count == 2
    assert bin_90_95.exact_match_accuracy == 1.0
    assert bin_90_95.exact_provenance_accuracy == 1.0
    assert final_bin.count == 1
    assert final_bin.exact_match_accuracy == 0.0
    assert final_bin.exact_provenance_accuracy == 0.0


def test_phase_31_cli_modes_emit_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert eval_main(
        [
            "--adversarial-suite",
            str(ROOT / "evals" / "suites" / "phase_31_adversarial.json"),
        ]
    ) == 0
    adversarial = json.loads(capsys.readouterr().out)
    assert adversarial["suite_id"] == "phase_31_adversarial"
    assert adversarial["passed"] is True
    assert len(adversarial["pairs"]) == 4

    assert eval_main(
        [
            "--mutation-suite",
            str(ROOT / "evals" / "suites" / "phase_31_mutation.json"),
        ]
    ) == 0
    mutation = json.loads(capsys.readouterr().out)
    assert mutation["suite_id"] == "phase_31_mutation"
    assert mutation["source_sensitivity"] == 1.0
    assert len(mutation["mutations"]) == 4

    assert eval_main(
        [
            "--calibration-suite",
            str(ROOT / "evals" / "suites" / "phase_30_diverse_corpus_round_1.json"),
        ]
    ) == 0
    calibration = json.loads(capsys.readouterr().out)
    assert calibration["suite_id"] == "phase_30_diverse_corpus_round_1"
    assert calibration["total_data_points"] == 49
