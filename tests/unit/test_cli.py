import asyncio
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import tomllib

from extractor.cli import async_main, main, render_summary
from extractor.contracts import ApprovedSchemaMetadata


ROOT = Path(__file__).resolve().parents[2]


def write_config(config_dir: Path, audit_path: Path) -> None:
    config_dir.mkdir()
    (config_dir / "default.yaml").write_text(
        "\n".join(
            (
                "llm:",
                "  provider: anthropic",
                "  model: test-model",
                "  max_retries: 0",
                "  timeout_seconds: 30",
                "  max_output_tokens: 512",
                "  temperature: 0.0",
                "chunking:",
                "  tokenizer: cl100k_base",
                "  window_tokens: 100",
                "  overlap_tokens: 0",
                "execution:",
                "  max_stage_concurrency: 1",
                "  max_chunk_concurrency: 1",
                "  max_llm_attempts: 1",
                "audit:",
                f"  database_path: {audit_path}",
                "logging:",
                "  level: INFO",
                "  format: json",
                "prompts:",
                f"  directory: {ROOT / 'prompts'}",
                "domain_packs:",
                f"  directory: {config_dir / 'domain_packs'}",
                "schema_registry:",
                f"  directory: {config_dir / 'schema_registry'}",
                "",
            )
        ),
        encoding="utf-8",
    )


def fake_pipeline_result() -> SimpleNamespace:
    schema_metadata = ApprovedSchemaMetadata(
        schema_id="schema:abcdef123456",
        schema_version="1",
        schema_hash="a" * 64,
        source_kind="planner_generated",
        domain_pack_id=None,
        document_class=None,
        created_from="planner",
        refined_from_schema_id=None,
    )
    return SimpleNamespace(
        run_id="run-1",
        document=SimpleNamespace(doc_id="doc-1"),
        plan=SimpleNamespace(schema_metadata=schema_metadata),
        completed_manifest=SimpleNamespace(
            status="completed",
            audit_db_path="/tmp/audit.sqlite3",
            output_data_point_ids=("dp-1",),
        ),
        report=SimpleNamespace(
            output_path="/tmp/report.json",
            output_sha256="a" * 64,
            output_byte_length=123,
        ),
        reconciliation=SimpleNamespace(data_points=(SimpleNamespace(data_point_id="dp-1"),)),
        usage_summary={
            "critic": {
                "calls": 2,
                "input_tokens": 160,
                "output_tokens": 35,
                "cache_read_tokens": 50,
                "cache_creation_tokens": 5,
            }
        },
    )


def fake_refusal_result() -> SimpleNamespace:
    return SimpleNamespace(
        run_id="run-1",
        document=SimpleNamespace(doc_id="doc-1"),
        refusal=SimpleNamespace(
            reason_codes=("no_approved_schema_candidates",),
            candidate_schema_ids=(),
            model_dump=lambda mode="json": {
                "run_id": "run-1",
                "doc_id": "doc-1",
                "document_class": "financial_update",
                "domain_hints": ["finance"],
                "reason_codes": ["no_approved_schema_candidates"],
                "candidate_schema_ids": [],
                "fit_assessments": [],
                "policy": {
                    "require_approved_schema": True,
                    "minimum_schema_coverage": 0.65,
                    "allow_planner_generated_fallback": False,
                },
            },
        ),
        completed_manifest=SimpleNamespace(
            status="refused",
            audit_db_path="/tmp/audit.sqlite3",
            output_data_point_ids=(),
        ),
        report=SimpleNamespace(
            output_path="/tmp/refusal.json",
            output_sha256="b" * 64,
            output_byte_length=456,
        ),
        usage_summary={
            "planner.classify_document": {
                "calls": 1,
                "input_tokens": 10,
                "output_tokens": 5,
                "cache_read_tokens": 0,
                "cache_creation_tokens": 0,
            }
        },
    )


def test_render_summary_outputs_stable_json() -> None:
    payload = json.loads(render_summary(fake_pipeline_result()))

    assert payload == {
        "audit_db_path": "/tmp/audit.sqlite3",
        "data_point_count": 1,
        "doc_id": "doc-1",
        "outcome_type": "extraction_success",
        "output_byte_length": 123,
        "output_data_point_ids": ["dp-1"],
        "output_path": "/tmp/report.json",
        "output_sha256": "a" * 64,
        "run_id": "run-1",
        "schema_metadata": {
            "created_from": "planner",
            "document_class": None,
            "domain_pack_id": None,
            "refined_from_schema_id": None,
            "schema_hash": "a" * 64,
            "schema_id": "schema:abcdef123456",
            "schema_version": "1",
            "source_kind": "planner_generated",
        },
        "status": "completed",
        "usage_summary": {
            "critic": {
                "cache_creation_tokens": 5,
                "cache_read_tokens": 50,
                "calls": 2,
                "input_tokens": 160,
                "output_tokens": 35,
            }
        },
    }


def test_render_summary_outputs_refusal_identity() -> None:
    payload = json.loads(render_summary(fake_refusal_result()))

    assert payload == {
        "audit_db_path": "/tmp/audit.sqlite3",
        "data_point_count": 0,
        "doc_id": "doc-1",
        "outcome_type": "schema_fit_refusal",
        "output_byte_length": 456,
        "output_data_point_ids": [],
        "output_path": "/tmp/refusal.json",
        "output_sha256": "b" * 64,
        "refusal": {
            "candidate_schema_ids": [],
            "doc_id": "doc-1",
            "document_class": "financial_update",
            "domain_hints": ["finance"],
            "fit_assessments": [],
            "policy": {
                "allow_planner_generated_fallback": False,
                "minimum_schema_coverage": 0.65,
                "require_approved_schema": True,
            },
            "reason_codes": ["no_approved_schema_candidates"],
            "run_id": "run-1",
        },
        "run_id": "run-1",
        "status": "refused",
        "usage_summary": {
            "planner.classify_document": {
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "calls": 1,
                "input_tokens": 10,
                "output_tokens": 5,
            }
        },
    }


def test_async_main_loads_config_runs_pipeline_and_prints_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fake_run_extraction_pipeline(**kwargs: object) -> SimpleNamespace:
        observed.update(kwargs)
        return fake_pipeline_result()

    async def run_check() -> None:
        source = tmp_path / "source.txt"
        source.write_text("Revenue increased.", encoding="utf-8")
        output = tmp_path / "report.json"
        config_dir = tmp_path / "config"
        write_config(config_dir, tmp_path / "audit.sqlite3")
        cli_main = importlib.import_module("extractor.cli.main")
        monkeypatch.setattr(cli_main, "run_extraction_pipeline", fake_run_extraction_pipeline)

        status = await async_main(
            (
                str(source),
                "--output",
                str(output),
                "--config-dir",
                str(config_dir),
                "--no-local-config",
                "--run-id",
                "run-1",
                "--resume",
                "--domain-hint",
                "finance",
                "--domain-hint",
                "earnings",
            )
        )

        assert status == 0

    observed: dict[str, object] = {}
    asyncio.run(run_check())
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload["run_id"] == "run-1"
    assert observed["source_path"] == tmp_path / "source.txt"
    assert observed["output_path"] == tmp_path / "report.json"
    assert observed["run_id"] == "run-1"
    assert observed["resume"] is True
    assert observed["domain_hints"] == ("finance", "earnings")
    assert observed["config"].audit.database_path == tmp_path / "audit.sqlite3"


def test_main_returns_nonzero_for_missing_source(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_dir = tmp_path / "config"
    write_config(config_dir, tmp_path / "audit.sqlite3")

    status = main(
        (
            str(tmp_path / "missing.txt"),
            "--output",
            str(tmp_path / "report.json"),
            "--config-dir",
            str(config_dir),
            "--no-local-config",
        )
    )

    captured = capsys.readouterr()
    assert status == 1
    assert "CliError" in captured.err
    assert "does not exist" in captured.err


def test_pyproject_registers_console_script() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["veritext"] == "extractor.cli.main:main"
    assert pyproject["project"]["scripts"]["veritext-audit"] == "extractor.audit.cli:main"
