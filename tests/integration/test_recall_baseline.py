from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path

import pytest

from extractor.audit import AuditStore
from extractor.config import load_config
from extractor.evals import (
    evaluate_report,
    evaluate_report_file,
    load_evaluation_case,
    summarize_run_drops,
)
from extractor.evals.scoring import load_extraction_report
from extractor.orchestrator import run_extraction_pipeline


ROOT = Path(__file__).resolve().parents[2]
CASE_PATH = ROOT / "evals" / "fixtures" / "medium_research_brief" / "case.json"
BASELINE_PATH = ROOT / "evals" / "baselines" / "medium_research_brief.json"
SNAPSHOT_REPORT = ROOT / "outputs" / "medium-research-2.json"


def _load_baseline() -> dict[str, object]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _assert_meets_baseline(metrics, baseline_metrics: dict[str, float]) -> None:
    assert metrics.recall >= baseline_metrics["recall"], (
        f"recall regressed: {metrics.recall:.4f} < baseline {baseline_metrics['recall']:.4f}"
    )
    assert metrics.precision >= baseline_metrics["precision"], (
        f"precision regressed: {metrics.precision:.4f} < baseline {baseline_metrics['precision']:.4f}"
    )
    assert metrics.provenance_recall >= baseline_metrics["provenance_recall"], (
        f"provenance_recall regressed: {metrics.provenance_recall:.4f} "
        f"< baseline {baseline_metrics['provenance_recall']:.4f}"
    )
    assert metrics.invariant_violation_count <= baseline_metrics["invariant_violation_count"], (
        f"invariant violations grew: {metrics.invariant_violation_count} "
        f"> baseline {baseline_metrics['invariant_violation_count']}"
    )


def test_case_loads_and_validates() -> None:
    case = load_evaluation_case(CASE_PATH)
    assert case.case_id == "medium_research_brief"
    assert len(case.expected_data_points) > 0


def test_snapshot_report_meets_baseline() -> None:
    """Score the pinned snapshot report against the case.

    Catches: scorer regressions, EvaluationCase schema drift, accidental edits to
    outputs/medium-research-2.json. Always-on guard for the eval harness itself.
    """
    if not SNAPSHOT_REPORT.exists():
        pytest.skip(f"snapshot report missing: {SNAPSHOT_REPORT}")

    baseline = _load_baseline()
    result = evaluate_report_file(CASE_PATH, SNAPSHOT_REPORT)
    _assert_meets_baseline(result.metrics, baseline["metrics"])


@pytest.mark.live_eval
def test_live_pipeline_meets_baseline(tmp_path: Path) -> None:
    """Run the real LLM pipeline against the fixture and gate on baseline metrics.

    Opt-in: set VERITEXT_RUN_LIVE_EVAL=1. Costs real API tokens (~$0.80 per the
    medium-fixture estimate). Use before merging any Phase 2 cost-reduction
    change to verify recall did not regress.
    """
    if os.environ.get("VERITEXT_RUN_LIVE_EVAL") != "1":
        pytest.skip("set VERITEXT_RUN_LIVE_EVAL=1 to run the live pipeline eval")

    case = load_evaluation_case(CASE_PATH)
    baseline = _load_baseline()
    config = load_config(include_local=False)
    output_path = tmp_path / "report.json"
    run_id = f"recall-baseline-{uuid.uuid4().hex[:8]}"

    async def run() -> tuple[object, object]:
        pipeline_result = await run_extraction_pipeline(
            source_path=case.source_path,
            output_path=output_path,
            config=config,
            run_id=run_id,
        )
        async with AuditStore(config.audit.database_path) as store:
            drops_result = await summarize_run_drops(store, run_id)
        return pipeline_result, drops_result

    pipeline_result, drops = asyncio.run(run())
    report = load_extraction_report(output_path)
    eval_result = evaluate_report(case, report)

    print(
        json.dumps(
            {
                "run_id": run_id,
                "metrics": eval_result.metrics.model_dump(mode="json"),
                "baseline_metrics": baseline["metrics"],
                "usage_summary": pipeline_result.usage_summary,
                "baseline_usage_summary": baseline["usage_summary"],
                "drops": drops.model_dump(mode="json"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    _assert_meets_baseline(eval_result.metrics, baseline["metrics"])
