import json
import tomllib
from pathlib import Path

import pytest

from extractor.evals import EvaluationError, evaluate_report, load_evaluation_case
from extractor.evals.cli import main as eval_main
from extractor.reporter import ExtractionReport


ROOT = Path(__file__).resolve().parents[2]
CASE_PATH = ROOT / "evals" / "fixtures" / "minimal_financial_update" / "expected.json"
REPORT_PATH = ROOT / "evals" / "fixtures" / "minimal_financial_update" / "report.example.json"
FIXTURE_DIRS = (
    ROOT / "evals" / "fixtures" / "minimal_financial_update",
    ROOT / "evals" / "fixtures" / "minimal_contract_obligation",
    ROOT / "evals" / "fixtures" / "minimal_policy_controls",
    ROOT / "evals" / "fixtures" / "hard_mixed_distractors",
    ROOT / "evals" / "fixtures" / "legal_contracts_core",
)


def load_report() -> ExtractionReport:
    return ExtractionReport.model_validate_json(REPORT_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("fixture_dir", FIXTURE_DIRS)
def test_evaluate_report_scores_exact_fixtures_as_passing(fixture_dir: Path) -> None:
    case = load_evaluation_case(fixture_dir / "expected.json")
    report = ExtractionReport.model_validate_json(
        (fixture_dir / "report.example.json").read_text(encoding="utf-8")
    )
    result = evaluate_report(case, report)

    assert result.passed is True
    assert result.metrics.precision == 1.0
    assert result.metrics.recall == 1.0
    assert result.metrics.f1 == 1.0
    assert result.metrics.provenance_recall == 1.0
    assert result.metrics.invariant_violation_count == 0
    assert result.missing_expected_ids == ()
    assert result.unexpected_data_point_ids == ()


def test_evaluate_report_counts_missing_and_unexpected_points() -> None:
    case = load_evaluation_case(CASE_PATH)
    report = load_report()
    dropped_first = report.data_points[1:]
    unexpected = report.data_points[0].model_copy(
        update={
            "data_point_id": "dp-unexpected",
            "category": "Unexpected",
            "field_name": "statement",
        }
    )
    report = report.model_copy(
        update={
            "data_points": (*dropped_first, unexpected),
            "output_data_point_ids": tuple(
                point.data_point_id for point in (*dropped_first, unexpected)
            ),
        }
    )

    result = evaluate_report(case, report)

    assert result.passed is False
    assert result.metrics.true_positives == 2
    assert result.metrics.false_positives == 1
    assert result.metrics.false_negatives == 1
    assert result.metrics.precision == pytest.approx(2 / 3)
    assert result.metrics.recall == pytest.approx(2 / 3)
    assert result.missing_expected_ids == ("expected-revenue-growth",)
    assert result.unexpected_data_point_ids == ("dp-unexpected",)


def test_evaluate_report_flags_source_span_invariant_breaks() -> None:
    case = load_evaluation_case(CASE_PATH)
    report = load_report()
    shifted = report.data_points[0].source_span.model_copy(
        update={
            "start_char": 1,
            "end_char": 22,
            "start_byte": 1,
            "end_byte": 22,
        }
    )
    broken_point = report.data_points[0].model_copy(update={"source_span": shifted})
    report = report.model_copy(update={"data_points": (broken_point, *report.data_points[1:])})

    result = evaluate_report(case, report)

    assert result.passed is False
    assert result.metrics.true_positives == 3
    assert result.metrics.provenance_recall == pytest.approx(2 / 3)
    assert {violation.code for violation in result.invariant_violations} == {
        "source_span_byte_mismatch",
        "source_span_text_mismatch",
    }


def test_load_evaluation_case_rejects_bad_expected_provenance(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "case"
    fixture_dir.mkdir()
    (fixture_dir / "source.txt").write_text("Revenue increased 12%.", encoding="utf-8")
    bad_case = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    bad_case["source_path"] = "source.txt"
    bad_case["expected_data_points"][0]["source_text"] = "Revenue invented 12%"
    (fixture_dir / "expected.json").write_text(json.dumps(bad_case), encoding="utf-8")

    with pytest.raises(EvaluationError, match="Invalid evaluation case"):
        load_evaluation_case(fixture_dir / "expected.json")


def test_hard_mixed_fixture_contains_unexpected_distractors() -> None:
    fixture_dir = ROOT / "evals" / "fixtures" / "hard_mixed_distractors"
    case = load_evaluation_case(fixture_dir / "expected.json")

    assert "prior target was 15%" in case.source_text
    assert "sample customer Alpha LLC" in case.source_text
    assert all("15%" not in point.value for point in case.expected_data_points)
    assert all("Alpha LLC" not in point.value for point in case.expected_data_points)


def test_legal_contract_fixture_report_cites_approved_schema_metadata() -> None:
    fixture_dir = ROOT / "evals" / "fixtures" / "legal_contracts_core"
    report = ExtractionReport.model_validate_json(
        (fixture_dir / "report.example.json").read_text(encoding="utf-8")
    )

    assert report.schema_metadata.schema_id == "schema:legal-contract-core-v1"
    assert report.schema_metadata.schema_version == "1.0.0"
    assert (
        report.schema_metadata.schema_hash
        == "4d4c5da3c52962339a2cedfa246ecf22ad2be0f003e8de62f5d3a162d2f62dc4"
    )
    assert report.schema_metadata.source_kind == "schema_registry"
    assert report.schema_metadata.domain_pack_id == "legal-contracts-v1"
    assert report.schema_metadata.document_class == "legal_contract"


def test_eval_cli_returns_zero_for_passing_fixture(capsys: pytest.CaptureFixture[str]) -> None:
    status = eval_main((str(CASE_PATH), str(REPORT_PATH)))

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert status == 0
    assert payload["passed"] is True
    assert payload["metrics"]["f1"] == 1.0


def test_pyproject_registers_eval_console_script() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["veritext-eval"] == "extractor.evals.cli:main"
