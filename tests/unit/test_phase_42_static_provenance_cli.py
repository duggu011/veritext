from __future__ import annotations

import asyncio
import json
from pathlib import Path

from extractor.audit import AuditStore
from extractor.reporter import write_report
from extractor.reporter.cli import async_main
from tests.unit.test_phase_40_report_cli import ROOT
from tests.unit.test_reporter import (
    COMPLETED,
    make_data_point,
    make_manifest,
    make_schema_metadata,
    seed_audit_store,
)


def test_report_cli_provenance_writes_static_html_artifact(tmp_path, capsys) -> None:
    async def run_check() -> int:
        report_path = tmp_path / "report.json"
        output_path = tmp_path / "report.provenance.html"
        audit_path = tmp_path / "audit.sqlite3"
        data_point = make_data_point().model_copy(update={"confidence": 0.91})
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

        return await async_main(
            (
                "provenance",
                str(report_path),
                "--audit-db",
                str(audit_path),
                "--output",
                str(output_path),
                "--config-dir",
                str(ROOT / "config"),
                "--no-local-config",
            )
        )

    status = asyncio.run(run_check())
    payload = json.loads(capsys.readouterr().out)
    output_path = Path(payload["output_path"])
    html = output_path.read_text(encoding="utf-8")

    assert status == 0
    assert payload["outcome_type"] == "static_provenance_written"
    assert payload["run_id"] == "run-1"
    assert payload["doc_id"] == "doc-1"
    assert payload["data_point_count"] == 1
    assert payload["warning_count"] == 2
    assert len(payload["output_sha256"]) == 64
    assert payload["output_byte_length"] == output_path.stat().st_size
    assert 'id="data-point-dp-1"' in html
    assert "Revenue increased" in html


def test_report_cli_provenance_rejects_missing_audited_document(tmp_path) -> None:
    async def run_check() -> None:
        report_path = tmp_path / "report.json"
        output_path = tmp_path / "report.provenance.html"
        audit_path = tmp_path / "audit.sqlite3"
        data_point = make_data_point()
        async with AuditStore(audit_path) as audit_store:
            await audit_store.record_run_manifest(make_manifest())
            await write_report(
                manifest=make_manifest(),
                data_points=(data_point,),
                schema_metadata=make_schema_metadata(),
                output_path=report_path,
                audit_store=None,
                generated_at=COMPLETED,
            )

        await async_main(
            (
                "provenance",
                str(report_path),
                "--audit-db",
                str(audit_path),
                "--output",
                str(output_path),
                "--config-dir",
                str(ROOT / "config"),
                "--no-local-config",
            )
        )

    import pytest

    with pytest.raises(Exception, match="Audited document not found"):
        asyncio.run(run_check())
