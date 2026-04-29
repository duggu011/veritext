from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from extractor.evals.scoring import EvaluationError, evaluate_report_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="veritext-eval",
        description="Score a Veritext extraction report against a source-backed eval fixture.",
    )
    parser.add_argument("case", type=Path, help="Evaluation case JSON path.")
    parser.add_argument("report", type=Path, help="Extraction report JSON path.")
    return parser


def render_result(result: object) -> str:
    return json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = evaluate_report_file(args.case, args.report)
    except EvaluationError as exc:
        print(f"{exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1
    print(render_result(result))
    return 0 if result.passed else 2


__all__ = ["build_parser", "main", "render_result"]
