from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Sequence

from extractor.config import ConfigError, configure_logging, load_config
from extractor.orchestrator import run_extraction_pipeline


class CliError(RuntimeError):
    """Raised when command-line arguments cannot start a pipeline run."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="veritext",
        description="Run the auditable Veritext extraction pipeline.",
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Source document path (.txt, .md, or .pdf).",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        type=Path,
        help="Output report JSON path.",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing default.yaml and optional local.yaml.",
    )
    parser.add_argument(
        "--no-local-config",
        action="store_true",
        help="Ignore config/local.yaml even when it exists.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Stable run ID to use instead of generating one.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume an existing failed or interrupted run_id from audited state.",
    )
    parser.add_argument(
        "--domain-hint",
        action="append",
        default=[],
        help="Domain hint to pass to planning. May be repeated.",
    )
    return parser


async def async_main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.source.is_file():
        raise CliError(f"Source document does not exist or is not a file: {args.source}")

    try:
        config = load_config(
            config_dir=args.config_dir,
            include_local=not args.no_local_config,
        )
    except ConfigError:
        raise

    configure_logging(config.logging)
    result = await run_extraction_pipeline(
        source_path=args.source,
        output_path=args.output,
        config=config,
        run_id=args.run_id,
        domain_hints=tuple(args.domain_hint),
        resume=args.resume,
    )
    print(render_summary(result))
    return 0


def render_summary(result: object) -> str:
    summary = {
        "run_id": result.run_id,
        "doc_id": result.document.doc_id,
        "schema_metadata": result.plan.schema_metadata.model_dump(mode="json"),
        "status": result.completed_manifest.status,
        "audit_db_path": result.completed_manifest.audit_db_path,
        "output_path": result.report.output_path,
        "output_sha256": result.report.output_sha256,
        "output_byte_length": result.report.output_byte_length,
        "data_point_count": len(result.reconciliation.data_points),
        "output_data_point_ids": result.completed_manifest.output_data_point_ids,
        "usage_summary": result.usage_summary,
    }
    return json.dumps(summary, sort_keys=True)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return asyncio.run(async_main(argv))
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"{exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1


__all__ = ["CliError", "async_main", "build_parser", "main", "render_summary"]
