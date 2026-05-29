from __future__ import annotations

import asyncio
import json
from pathlib import Path

import tomllib

from extractor.audit import AuditStore
from extractor.reporter import write_report
from extractor.reporter.cli import async_main
from tests.unit.test_phase_40_run_diff import GENERATED, make_report
from tests.unit.test_reporter import (
    COMPLETED,
    make_data_point,
    make_manifest,
    make_schema_metadata,
    seed_audit_store,
)


ROOT = Path(__file__).resolve().parents[2]


def test_report_cli_diff_writes_run_diff_json(tmp_path, capsys) -> None:
    base_report = make_report(
        run_id="run-1",
        data_points=(make_data_point(data_point_id="dp-1"),),
    )
    candidate_report = make_report(
        run_id="run-2",
        data_points=(
            make_data_point(data_point_id="dp-2").model_copy(update={"run_id": "run-2"}),
        ),
    )
    base_path = tmp_path / "base.json"
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "diff.json"
    base_path.write_text(
        json.dumps(base_report.model_dump(mode="json"), sort_keys=True),
        encoding="utf-8",
    )
    candidate_path.write_text(
        json.dumps(candidate_report.model_dump(mode="json"), sort_keys=True),
        encoding="utf-8",
    )

    status = asyncio.run(
        async_main(
            (
                "diff",
                str(base_path),
                str(candidate_path),
                "--output",
                str(output_path),
                "--diff-run-id",
                "diff-run-1-run-2",
            )
        )
    )

    payload = json.loads(capsys.readouterr().out)
    diff_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert status == 0
    assert payload["outcome_type"] == "run_diff_written"
    assert payload["summary_counts"]["unchanged"] == 1
    assert diff_payload["report_schema_version"] == "run_diff_report.v1"


def test_report_cli_sign_and_verify_report_manifest(tmp_path, monkeypatch, capsys) -> None:
    async def run_check() -> tuple[int, int]:
        report_path = tmp_path / "report.json"
        audit_path = tmp_path / "audit.sqlite3"
        data_point = make_data_point().model_copy(update={"confidence": 0.9})
        async with AuditStore(audit_path) as audit_store:
            await seed_audit_store(audit_store, make_manifest(), (data_point,))
            await write_report(
                manifest=make_manifest(),
                data_points=(data_point,),
                schema_metadata=make_schema_metadata(),
                output_path=report_path,
                audit_store=audit_store,
                generated_at=COMPLETED,
            )

        sign_status = await async_main(
            (
                "sign",
                str(report_path),
                "--audit-db",
                str(audit_path),
                "--config-dir",
                str(ROOT / "config"),
                "--no-local-config",
            )
        )
        verify_status = await async_main(
            (
                "verify",
                str(report_path),
                str(report_path.with_name(f"{report_path.name}.manifest.json")),
                "--config-dir",
                str(ROOT / "config"),
                "--no-local-config",
            )
        )
        return sign_status, verify_status

    monkeypatch.setenv("REPORT_SIGNING_KEY", "phase-40-secret")

    sign_status, verify_status = asyncio.run(run_check())

    output_lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert sign_status == 0
    assert verify_status == 0
    assert output_lines[0]["outcome_type"] == "report_manifest_signed"
    assert output_lines[1]["verified"] is True


def test_pyproject_registers_report_console_script() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["veritext-report"] == "extractor.reporter.cli:main"
