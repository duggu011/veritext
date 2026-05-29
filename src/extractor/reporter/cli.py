from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Sequence

from extractor.audit import AuditStore
from extractor.config import ConfigError, load_config
from extractor.contracts import SignedReportManifest
from extractor.reporter import (
    ExtractionReport,
    ReportWriteResult,
    diff_reports,
    file_sha256,
    verify_signed_report_manifest,
    write_run_diff_report,
    write_signed_report_manifest,
)


class ReportCliError(RuntimeError):
    """Raised when report CLI arguments cannot produce a valid artifact."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="veritext-report",
        description="Sign, verify, and diff Veritext report artifacts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    diff_parser = subparsers.add_parser("diff", help="Write a deterministic run diff report.")
    diff_parser.add_argument("base_report", type=Path)
    diff_parser.add_argument("candidate_report", type=Path)
    diff_parser.add_argument("-o", "--output", required=True, type=Path)
    diff_parser.add_argument("--diff-run-id", required=True)

    sign_parser = subparsers.add_parser("sign", help="Write a detached signed report manifest.")
    sign_parser.add_argument("report", type=Path)
    sign_parser.add_argument("--audit-db", required=True, type=Path)
    sign_parser.add_argument("--manifest-output", type=Path, default=None)
    _add_config_args(sign_parser)

    verify_parser = subparsers.add_parser("verify", help="Verify a report against a manifest.")
    verify_parser.add_argument("report", type=Path)
    verify_parser.add_argument("manifest", type=Path)
    _add_config_args(verify_parser)

    return parser


async def async_main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "diff":
        return _run_diff(args)
    if args.command == "sign":
        return await _run_sign(args)
    if args.command == "verify":
        return _run_verify(args)
    raise ReportCliError(f"Unsupported report command: {args.command}")


def _run_diff(args: argparse.Namespace) -> int:
    base_report = _load_extraction_report(args.base_report)
    candidate_report = _load_extraction_report(args.candidate_report)
    report = diff_reports(
        base_report=base_report,
        candidate_report=candidate_report,
        diff_run_id=args.diff_run_id,
        generated_at=_max_generated_at(base_report, candidate_report),
    )
    result = write_run_diff_report(report=report, output_path=args.output)
    print(
        _json_line(
            {
                "outcome_type": "run_diff_written",
                "diff_run_id": report.diff_run_id,
                "output_path": result.output_path,
                "output_sha256": result.output_sha256,
                "output_byte_length": result.output_byte_length,
                "summary_counts": report.summary_counts,
            }
        )
    )
    return 0


async def _run_sign(args: argparse.Namespace) -> int:
    config = _load_cli_config(args)
    report = _load_extraction_report(args.report)
    async with AuditStore(args.audit_db) as audit_store:
        completed_manifest = await audit_store.get_run_manifest(report.run_id)
        if completed_manifest is None:
            raise ReportCliError(f"Run manifest not found in audit DB: {report.run_id}")
        result = ReportWriteResult(
            report=report,
            output_path=str(args.report),
            output_sha256=file_sha256(args.report),
            output_byte_length=args.report.stat().st_size,
            completed_manifest=completed_manifest,
        )
        manifest = await write_signed_report_manifest(
            report_result=result,
            audit_store=audit_store,
            config=config,
            manifest_path=args.manifest_output,
        )

    manifest_path = args.manifest_output or args.report.with_name(
        f"{args.report.name}{config.reporting.signing.manifest_suffix}"
    )
    print(
        _json_line(
            {
                "outcome_type": "report_manifest_signed",
                "run_id": report.run_id,
                "manifest_path": str(manifest_path),
                "artifact_sha256": manifest.artifact.artifact_sha256,
                "signed_payload_sha256": manifest.signature.signed_payload_sha256,
                "key_id": manifest.signature.key_id,
            }
        )
    )
    return 0


def _run_verify(args: argparse.Namespace) -> int:
    config = _load_cli_config(args)
    manifest = SignedReportManifest.model_validate_json(args.manifest.read_text(encoding="utf-8"))
    verified = verify_signed_report_manifest(
        report_path=args.report,
        manifest=manifest,
        config=config,
    )
    print(
        _json_line(
            {
                "outcome_type": "report_manifest_verified",
                "verified": verified,
                "artifact_sha256": manifest.artifact.artifact_sha256,
                "key_id": manifest.signature.key_id,
            }
        )
    )
    return 0 if verified else 1


def _load_extraction_report(path: Path) -> ExtractionReport:
    if not path.is_file():
        raise ReportCliError(f"Report does not exist or is not a file: {path}")
    raw_report = path.read_text(encoding="utf-8")
    payload = json.loads(raw_report)
    if payload.get("report_schema_version") != "report.v2":
        raise ReportCliError("Only report.v2 is supported by this command")
    return ExtractionReport.model_validate_json(raw_report)


def _load_cli_config(args: argparse.Namespace):
    try:
        return load_config(
            config_dir=args.config_dir,
            include_local=not args.no_local_config,
        )
    except ConfigError:
        raise


def _add_config_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config-dir", type=Path, default=None)
    parser.add_argument("--no-local-config", action="store_true")


def _max_generated_at(base_report: ExtractionReport, candidate_report: ExtractionReport):
    return max(base_report.generated_at, candidate_report.generated_at)


def _json_line(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return asyncio.run(async_main(argv))
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"{exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1


__all__ = ["ReportCliError", "async_main", "build_parser", "main"]
