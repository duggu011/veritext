from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

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
    return parser


def render_result(result: object) -> str:
    return json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.suite is not None and (args.case is not None or args.report is not None):
        parser.error("--suite cannot be combined with case/report arguments")
    if args.suite is None and (args.case is None or args.report is None):
        parser.error("case and report are required unless --suite is provided")

    try:
        if args.suite is not None:
            result = evaluate_suite_manifest(args.suite)
        else:
            result = evaluate_report_file(args.case, args.report)
    except EvaluationError as exc:
        print(f"{exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1
    print(render_result(result))
    return 0 if result.passed else 2


__all__ = ["build_parser", "main", "render_result"]
