import asyncio
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import tomllib

from extractor.cli import async_main, main, render_summary


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
                "",
            )
        ),
        encoding="utf-8",
    )


def fake_pipeline_result() -> SimpleNamespace:
    return SimpleNamespace(
        run_id="run-1",
        document=SimpleNamespace(doc_id="doc-1"),
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


def test_render_summary_outputs_stable_json() -> None:
    payload = json.loads(render_summary(fake_pipeline_result()))

    assert payload == {
        "audit_db_path": "/tmp/audit.sqlite3",
        "data_point_count": 1,
        "doc_id": "doc-1",
        "output_byte_length": 123,
        "output_data_point_ids": ["dp-1"],
        "output_path": "/tmp/report.json",
        "output_sha256": "a" * 64,
        "run_id": "run-1",
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
