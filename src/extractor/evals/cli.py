from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from extractor.evals.calibration import generate_calibration_report
from extractor.evals.robustness import (
    evaluate_adversarial_manifest,
    evaluate_mutation_manifest,
)
from extractor.evals.scoring import EvaluationError, evaluate_report_file
from extractor.evals.suites import evaluate_suite_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="veritext-eval",
        description="Score a Veritext extraction report against a source-backed eval fixture.",
    )
    parser.add_argument(
        "case",
        nargs="?",
        type=Path,
        help="Evaluation case JSON path.",
    )
    parser.add_argument(
        "report",
        nargs="?",
        type=Path,
        help="Extraction report JSON path.",
    )
    parser.add_argument("--suite", type=Path, help="Evaluation suite manifest JSON path.")
    parser.add_argument(
        "--adversarial-suite",
        type=Path,
        help="Phase 31 adversarial manifest JSON path.",
    )
    parser.add_argument(
        "--mutation-suite",
        type=Path,
        help="Phase 31 mutation manifest JSON path.",
    )
    parser.add_argument(
        "--calibration-suite",
        type=Path,
        help="Evaluation suite manifest JSON path for calibration output.",
    )
    return parser


def render_result(result: object) -> str:
    return json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    suite_modes = (
        args.suite,
        args.adversarial_suite,
        args.mutation_suite,
        args.calibration_suite,
    )
    if sum(mode is not None for mode in suite_modes) > 1:
        parser.error("suite modes cannot be combined")
    if any(mode is not None for mode in suite_modes) and (
        args.case is not None or args.report is not None
    ):
        parser.error("suite modes cannot be combined with case/report arguments")
    if all(mode is None for mode in suite_modes) and (
        args.case is None or args.report is None
    ):
        parser.error("case and report are required unless a suite mode is provided")

    try:
        if args.adversarial_suite is not None:
            result = evaluate_adversarial_manifest(args.adversarial_suite)
        elif args.mutation_suite is not None:
            result = evaluate_mutation_manifest(args.mutation_suite)
        elif args.calibration_suite is not None:
            result = generate_calibration_report(args.calibration_suite)
        elif args.suite is not None:
            result = evaluate_suite_manifest(args.suite)
        else:
            result = evaluate_report_file(args.case, args.report)
    except EvaluationError as exc:
        print(f"{exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1
    print(render_result(result))
    return 0 if result.passed else 2


__all__ = ["build_parser", "main", "render_result"]
