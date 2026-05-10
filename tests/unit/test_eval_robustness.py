import copy
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from extractor.evals import EvaluationError
from extractor.evals.scoring import (
    evaluate_report,
    load_evaluation_case,
    load_extraction_report,
)


ROOT = Path(__file__).resolve().parents[2]


def _valid_pair() -> dict[str, Any]:
    return {
        "pair_id": "financial-to-sec-paraphrase",
        "mode": "paraphrase",
        "base_fixture_id": "minimal_financial_update",
        "variant_fixture_id": "sec_market_disclosure",
        "base_case_path": "evals/fixtures/minimal_financial_update/expected.json",
        "base_report_path": "evals/fixtures/minimal_financial_update/report.example.json",
        "variant_case_path": "evals/fixtures/sec_market_disclosure/expected.json",
        "variant_report_path": "evals/fixtures/sec_market_disclosure/report.example.json",
    }


def _valid_manifest() -> dict[str, Any]:
    return {
        "suite_id": "unit_adversarial",
        "description": "Unit-test adversarial manifest for robustness validation.",
        "pairs": [_valid_pair()],
    }


def _write_manifest(
    tmp_path: Path,
    payload: dict[str, Any],
    *,
    filename: str = "adversarial.json",
) -> Path:
    manifest_path = tmp_path / filename
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    return manifest_path


def _copy_fixture(repo_root: Path, fixture_id: str, target_id: str) -> Path:
    target_dir = repo_root / "evals" / "fixtures" / target_id
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "evals" / "fixtures" / fixture_id, target_dir)
    return target_dir


def _build_minimal_mutation_fixture(
    repo_root: Path,
    *,
    retain_retired_report_value: bool = False,
) -> tuple[str, str]:
    base_dir = _copy_fixture(repo_root, "minimal_financial_update", "mutation_base")
    mutated_dir = _copy_fixture(
        repo_root,
        "minimal_financial_update",
        "mutation_revenue_increase",
    )
    retired_value = "Revenue increased 12%"
    introduced_value = "Revenue increased 18%"
    assert len(retired_value) == len(introduced_value)

    source_path = mutated_dir / "source.txt"
    source_text = source_path.read_text(encoding="utf-8")
    source_path.write_text(
        source_text.replace(retired_value, introduced_value),
        encoding="utf-8",
    )

    expected_path = mutated_dir / "expected.json"
    expected_payload = json.loads(expected_path.read_text(encoding="utf-8"))
    expected_payload["case_id"] = "mutation_revenue_increase"
    expected_payload["expected_data_points"][0]["source_text"] = introduced_value
    expected_payload["expected_data_points"][0]["value"] = introduced_value
    expected_path.write_text(json.dumps(expected_payload), encoding="utf-8")

    report_path = mutated_dir / "report.example.json"
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    report_payload["run_id"] = "run-mutation-revenue-increase"
    report_payload["doc_id"] = "doc-mutation-revenue-increase"
    first_point = report_payload["data_points"][0]
    first_point["run_id"] = report_payload["run_id"]
    first_point["doc_id"] = report_payload["doc_id"]
    first_point["source_span"]["doc_id"] = report_payload["doc_id"]
    if not retain_retired_report_value:
        first_point["source_span"]["text"] = introduced_value
        first_point["value"] = introduced_value
    for point in report_payload["data_points"][1:]:
        point["run_id"] = report_payload["run_id"]
        point["doc_id"] = report_payload["doc_id"]
        point["source_span"]["doc_id"] = report_payload["doc_id"]
    report_path.write_text(json.dumps(report_payload), encoding="utf-8")

    base_expected_payload = json.loads(
        (base_dir / "expected.json").read_text(encoding="utf-8")
    )
    base_expected_payload["case_id"] = "mutation_base"
    (base_dir / "expected.json").write_text(
        json.dumps(base_expected_payload),
        encoding="utf-8",
    )
    return retired_value, introduced_value


def _valid_mutation_manifest(
    *,
    retired_value: str,
    introduced_value: str,
) -> dict[str, Any]:
    return {
        "suite_id": "unit_mutation",
        "description": "Unit-test mutation manifest for robustness validation.",
        "mutations": [
            {
                "mutation_id": "minimal-financial-revenue-rate",
                "base_fixture_id": "mutation_base",
                "mutated_fixture_id": "mutation_revenue_increase",
                "base_case_path": "evals/fixtures/mutation_base/expected.json",
                "base_report_path": "evals/fixtures/mutation_base/report.example.json",
                "mutated_case_path": (
                    "evals/fixtures/mutation_revenue_increase/expected.json"
                ),
                "mutated_report_path": (
                    "evals/fixtures/mutation_revenue_increase/report.example.json"
                ),
                "changes": [
                    {
                        "expected_id": "expected-revenue-growth",
                        "retired_source_value": retired_value,
                        "introduced_source_value": introduced_value,
                    }
                ],
            }
        ],
    }


def test_phase_31_adversarial_manifest_loads() -> None:
    from extractor.evals.robustness import load_adversarial_manifest

    manifest = load_adversarial_manifest(
        ROOT / "evals" / "suites" / "phase_31_adversarial.json",
        repo_root=ROOT,
    )

    assert manifest.suite_id == "phase_31_adversarial"
    assert "Phase 31 adversarial robustness suite" in manifest.description


def test_phase_31_adversarial_manifest_covers_variant_domains_and_scores() -> None:
    from extractor.evals.robustness import load_adversarial_manifest

    manifest = load_adversarial_manifest(
        ROOT / "evals" / "suites" / "phase_31_adversarial.json",
        repo_root=ROOT,
    )

    assert [pair.variant_fixture_id for pair in manifest.pairs] == [
        "sec_market_disclosure_adversarial_distractors",
        "regulatory_order_compliance_adversarial_distractors",
        "insurance_policy_coverage_adversarial_distractors",
        "procurement_rfp_requirements_adversarial_distractors",
    ]
    assert {pair.mode for pair in manifest.pairs} == {"distractor_insertion"}
    assert len({pair.base_fixture_id for pair in manifest.pairs}) == 4

    for pair in manifest.pairs:
        case = load_evaluation_case(ROOT / pair.variant_case_path)
        report = load_extraction_report(ROOT / pair.variant_report_path)
        result = evaluate_report(case, report)

        assert result.passed is True
        assert result.metrics.precision == 1.0
        assert result.metrics.recall == 1.0
        assert result.metrics.f1 == 1.0
        assert result.metrics.provenance_recall == 1.0
        assert result.metrics.invariant_violation_count == 0


def test_phase_31_mutation_manifest_loads() -> None:
    from extractor.evals.robustness import load_mutation_manifest

    manifest = load_mutation_manifest(
        ROOT / "evals" / "suites" / "phase_31_mutation.json",
        repo_root=ROOT,
    )

    assert manifest.suite_id == "phase_31_mutation"
    assert "Phase 31 mutation robustness suite" in manifest.description
    assert manifest.mutations == ()


def test_load_mutation_manifest_rejects_duplicate_ids_bad_paths_empty_changes_and_absent_retired_value(
    tmp_path: Path,
) -> None:
    from extractor.evals.robustness import load_mutation_manifest

    repo_root = tmp_path / "repo"
    retired_value, introduced_value = _build_minimal_mutation_fixture(repo_root)
    payload = _valid_mutation_manifest(
        retired_value=retired_value,
        introduced_value=introduced_value,
    )
    payload["mutations"].append(copy.deepcopy(payload["mutations"][0]))
    with pytest.raises(EvaluationError, match="duplicate mutation IDs"):
        load_mutation_manifest(
            _write_manifest(tmp_path, payload, filename="mutation.json"),
            repo_root=repo_root,
        )

    payload = _valid_mutation_manifest(
        retired_value=retired_value,
        introduced_value=introduced_value,
    )
    payload["mutations"][0]["mutated_report_path"] = (
        "evals/fixtures/mutation_revenue_increase/missing-report.json"
    )
    with pytest.raises(EvaluationError, match="mutated_report_path does not exist"):
        load_mutation_manifest(
            _write_manifest(tmp_path, payload, filename="mutation.json"),
            repo_root=repo_root,
        )

    payload = _valid_mutation_manifest(
        retired_value=retired_value,
        introduced_value=introduced_value,
    )
    payload["mutations"][0]["changes"] = []
    with pytest.raises(EvaluationError, match="Invalid mutation manifest"):
        load_mutation_manifest(
            _write_manifest(tmp_path, payload, filename="mutation.json"),
            repo_root=repo_root,
        )

    payload = _valid_mutation_manifest(
        retired_value="Revenue increased 99%",
        introduced_value=introduced_value,
    )
    with pytest.raises(EvaluationError, match="retired_source_value absent from base fixture"):
        load_mutation_manifest(
            _write_manifest(tmp_path, payload, filename="mutation.json"),
            repo_root=repo_root,
        )


def test_evaluate_mutation_manifest_reports_source_sensitivity(
    tmp_path: Path,
) -> None:
    from extractor.evals.robustness import evaluate_mutation_manifest

    repo_root = tmp_path / "repo"
    retired_value, introduced_value = _build_minimal_mutation_fixture(repo_root)
    payload = _valid_mutation_manifest(
        retired_value=retired_value,
        introduced_value=introduced_value,
    )

    result = evaluate_mutation_manifest(
        _write_manifest(tmp_path, payload, filename="mutation.json"),
        repo_root=repo_root,
    )

    assert result.passed is True
    assert result.source_sensitivity == 1.0
    assert len(result.mutations) == 1
    mutation_result = result.mutations[0]
    assert mutation_result.result.passed is True
    assert mutation_result.source_sensitivity == 1.0
    assert mutation_result.source_sensitivity_failures == ()


def test_evaluate_mutation_manifest_fails_when_report_keeps_retired_value(
    tmp_path: Path,
) -> None:
    from extractor.evals.robustness import evaluate_mutation_manifest

    repo_root = tmp_path / "repo"
    retired_value, introduced_value = _build_minimal_mutation_fixture(
        repo_root,
        retain_retired_report_value=True,
    )
    payload = _valid_mutation_manifest(
        retired_value=retired_value,
        introduced_value=introduced_value,
    )

    result = evaluate_mutation_manifest(
        _write_manifest(tmp_path, payload, filename="mutation.json"),
        repo_root=repo_root,
    )

    assert result.passed is False
    assert result.source_sensitivity == 0.0
    failure_codes = {
        failure.code for failure in result.mutations[0].source_sensitivity_failures
    }
    assert failure_codes == {
        "retired_value_retained",
        "introduced_value_missing",
    }


def test_load_adversarial_manifest_rejects_duplicate_pair_ids(
    tmp_path: Path,
) -> None:
    from extractor.evals.robustness import load_adversarial_manifest

    payload = _valid_manifest()
    payload["pairs"].append(copy.deepcopy(payload["pairs"][0]))

    with pytest.raises(EvaluationError, match="duplicate adversarial pair IDs"):
        load_adversarial_manifest(_write_manifest(tmp_path, payload), repo_root=ROOT)


def test_load_adversarial_manifest_rejects_bad_paths_and_modes(
    tmp_path: Path,
) -> None:
    from extractor.evals.robustness import load_adversarial_manifest

    payload = _valid_manifest()
    payload["pairs"][0]["base_case_path"] = "../outside.json"
    with pytest.raises(EvaluationError, match="base_case_path must be repo-relative"):
        load_adversarial_manifest(_write_manifest(tmp_path, payload), repo_root=ROOT)

    payload = _valid_manifest()
    payload["pairs"][0]["variant_report_path"] = (
        "evals/fixtures/sec_market_disclosure/missing-report.json"
    )
    with pytest.raises(EvaluationError, match="variant_report_path does not exist"):
        load_adversarial_manifest(_write_manifest(tmp_path, payload), repo_root=ROOT)

    payload = _valid_manifest()
    payload["pairs"][0]["mode"] = "model_hint"
    with pytest.raises(EvaluationError, match="Invalid adversarial manifest"):
        load_adversarial_manifest(_write_manifest(tmp_path, payload), repo_root=ROOT)


def test_load_adversarial_manifest_rejects_copied_offsets_for_changed_variant_text(
    tmp_path: Path,
) -> None:
    from extractor.evals.robustness import load_adversarial_manifest

    repo_root = tmp_path / "repo"
    _copy_fixture(repo_root, "minimal_financial_update", "base")
    variant_dir = _copy_fixture(repo_root, "minimal_financial_update", "variant")

    case_path = variant_dir / "expected.json"
    case_payload = json.loads(case_path.read_text(encoding="utf-8"))
    first_point = case_payload["expected_data_points"][0]
    replacement = "Operating profit 420%"
    assert len(replacement) == len(first_point["source_text"])

    source_path = variant_dir / "source.txt"
    source_text = source_path.read_text(encoding="utf-8")
    source_text = (
        source_text[: first_point["start_char"]]
        + replacement
        + source_text[first_point["end_char"] :]
    )
    source_path.write_text(source_text, encoding="utf-8")
    first_point["source_text"] = replacement
    first_point["value"] = replacement
    case_path.write_text(json.dumps(case_payload), encoding="utf-8")

    payload = {
        "suite_id": "unit_adversarial",
        "description": "Unit-test adversarial manifest.",
        "pairs": [
            {
                "pair_id": "copied-offsets",
                "mode": "paraphrase",
                "base_fixture_id": "base",
                "variant_fixture_id": "variant",
                "base_case_path": "evals/fixtures/base/expected.json",
                "base_report_path": "evals/fixtures/base/report.example.json",
                "variant_case_path": "evals/fixtures/variant/expected.json",
                "variant_report_path": "evals/fixtures/variant/report.example.json",
            }
        ],
    }

    with pytest.raises(EvaluationError, match="copied offsets with changed source text"):
        load_adversarial_manifest(_write_manifest(tmp_path, payload), repo_root=repo_root)
