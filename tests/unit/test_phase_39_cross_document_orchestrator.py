from __future__ import annotations

import asyncio
import importlib
import json
from pathlib import Path
from typing import Callable

import pytest

from extractor.audit import AuditStore
from extractor.orchestrator import OrchestratorError
from tests.unit.test_orchestrator import DeterministicLLMClient, make_config


def _batch_service() -> Callable[..., object]:
    module = importlib.import_module("extractor.orchestrator")
    service = getattr(module, "run_cross_document_reconciliation_batch", None)
    assert service is not None, "run_cross_document_reconciliation_batch must be exported"
    return service


def test_cross_document_batch_runs_inputs_and_writes_audited_report(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        source_a = tmp_path / "source-a.txt"
        source_b = tmp_path / "source-b.txt"
        source_a.write_text("Revenue increased. Document A.", encoding="utf-8")
        source_b.write_text("Revenue increased. Document B.", encoding="utf-8")
        output_path = tmp_path / "cross-document-report.json"
        config = make_config(tmp_path)

        result = await _batch_service()(
            source_paths=(source_a, source_b),
            output_path=output_path,
            config=config,
            llm_client=DeterministicLLMClient(),
            cross_document_run_id="xrun-batch",
            run_ids=("run-a", "run-b"),
            domain_hints=("finance",),
        )

        payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert result.cross_document_run_id == "xrun-batch"
        assert tuple(item.run_id for item in result.input_results) == ("run-a", "run-b")
        assert result.completed_manifest.status == "completed"
        assert result.completed_manifest == result.report.completed_manifest
        assert result.report.output_path == str(output_path)
        assert payload["report_schema_version"] == "cross_document_report.v1"
        assert payload["cross_document_run_id"] == "xrun-batch"
        assert payload["input_run_ids"] == ["run-a", "run-b"]

        assert len(result.reconciliation.groups) == 1
        group = result.reconciliation.groups[0]
        assert group.document_count == 2
        assert {source.run_id for source in group.sources} == {"run-a", "run-b"}
        assert {source["run_id"] for source in payload["groups"][0]["sources"]} == {
            "run-a",
            "run-b",
        }

        async with AuditStore(config.audit.database_path) as audit_store:
            stored_manifest = await audit_store.get_cross_document_run_manifest(
                "xrun-batch"
            )
            stored_result = await audit_store.get_cross_document_reconciliation_result(
                "xrun-batch"
            )

        assert stored_manifest == result.completed_manifest
        assert stored_result == result.reconciliation

    asyncio.run(run_check())


def test_cross_document_batch_validates_source_and_run_id_inputs(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        source_a = tmp_path / "source-a.txt"
        source_b = tmp_path / "source-b.txt"
        source_a.write_text("Revenue increased. Document A.", encoding="utf-8")
        source_b.write_text("Revenue increased. Document B.", encoding="utf-8")
        config = make_config(tmp_path)

        with pytest.raises(OrchestratorError, match="at least two source documents"):
            await _batch_service()(
                source_paths=(source_a,),
                output_path=tmp_path / "cross-document-report.json",
                config=config,
                llm_client=DeterministicLLMClient(),
            )

        with pytest.raises(OrchestratorError, match="run_ids must be unique"):
            await _batch_service()(
                source_paths=(source_a, source_b),
                output_path=tmp_path / "cross-document-report.json",
                config=config,
                llm_client=DeterministicLLMClient(),
                run_ids=("run-a", "run-a"),
            )

    asyncio.run(run_check())


def test_phase_39_keeps_cli_single_source_contract(tmp_path: Path) -> None:
    from extractor.cli.main import build_parser

    source_a = tmp_path / "source-a.txt"
    source_b = tmp_path / "source-b.txt"
    source_a.write_text("Revenue increased. Document A.", encoding="utf-8")
    source_b.write_text("Revenue increased. Document B.", encoding="utf-8")
    parser = build_parser()

    parsed = parser.parse_args([str(source_a), "-o", str(tmp_path / "single.json")])
    assert parsed.source == source_a

    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(
            [str(source_a), str(source_b), "-o", str(tmp_path / "batch.json")]
        )
    assert excinfo.value.code == 2
