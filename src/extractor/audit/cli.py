from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Sequence

from extractor.audit.inspection import AuditInspectionError, inspect_audit_database


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="veritext-audit",
        description="Inspect a Veritext SQLite audit database.",
    )
    parser.add_argument(
        "database",
        nargs="?",
        type=Path,
        default=Path(".veritext/audit.sqlite3"),
        help="SQLite audit database path. Defaults to .veritext/audit.sqlite3.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Run ID to inspect. Defaults to the latest run by started_at.",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Include LLM calls, candidates, reports, rejections, and data points.",
    )
    return parser


async def async_main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = await inspect_audit_database(
        args.database,
        run_id=args.run_id,
        include_details=args.details,
    )
    print(render_inspection(result))
    return 0


def render_inspection(result: dict[str, object]) -> str:
    return json.dumps(result, indent=2, sort_keys=True)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return asyncio.run(async_main(argv))
    except AuditInspectionError as exc:
        print(f"{exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1


__all__ = ["async_main", "build_parser", "main", "render_inspection"]
