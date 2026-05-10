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


def _write_manifest(tmp_path: Path, payload: dict[str, Any]) -> Path:
    manifest_path = tmp_path / "adversarial.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    return manifest_path


def _copy_fixture(repo_root: Path, fixture_id: str, target_id: str) -> Path:
    target_dir = repo_root / "evals" / "fixtures" / target_id
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "evals" / "fixtures" / fixture_id, target_dir)
    return target_dir


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
