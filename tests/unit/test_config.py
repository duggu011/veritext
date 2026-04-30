import asyncio
import json
import os
from io import StringIO
from pathlib import Path

import pytest
import structlog
from pydantic import ValidationError

from extractor.config import (
    ConfigError,
    LoggingConfig,
    RunContext,
    bind_run_context,
    configure_logging,
    get_run_context,
    load_config,
    maybe_run_context,
)


BASE_CONFIG = """\
llm:
  provider: anthropic
  model: claude-sonnet-4-5
  max_retries: 3
  timeout_seconds: 60
  max_output_tokens: 2048
  temperature: 0.0
chunking:
  tokenizer: cl100k_base
  window_tokens: 1200
  overlap_tokens: 120
execution:
  max_stage_concurrency: 4
  max_chunk_concurrency: 2
  max_llm_attempts: 2
audit:
  database_path: .veritext/audit.sqlite3
logging:
  level: INFO
  format: json
prompts:
  directory: prompts
"""


def write_config(path: Path, body: str = BASE_CONFIG) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "default.yaml").write_text(body, encoding="utf-8")


def test_default_config_file_loads() -> None:
    config = load_config(env={}, include_local=False)

    assert config.llm.provider == "anthropic"
    assert config.llm.api_key_env == "ANTHROPIC_API_KEY"
    assert config.llm.model == "claude-sonnet-4-6"
    assert config.llm.stage_overrides["planner"].model is None
    assert config.llm.stage_overrides["executor"].model is None
    assert config.llm.stage_overrides["reconciler"].model is None
    assert config.llm.prompt_cache_enabled is True
    assert config.execution.max_stage_concurrency == 4
    assert config.execution.max_chunk_concurrency == 2
    assert config.logging.format == "json"
    assert config.chunking.overlap_tokens < config.chunking.window_tokens


def test_local_example_config_loads_as_moonshot_balanced_preset(tmp_path: Path) -> None:
    write_config(tmp_path, body=(Path("config") / "default.yaml").read_text())
    (tmp_path / "local.yaml").write_text(
        (Path("config") / "local.example.yaml").read_text(),
        encoding="utf-8",
    )

    config = load_config(config_dir=tmp_path, env={})

    assert config.llm.provider == "openai_compatible"
    assert config.llm.base_url == "https://api.moonshot.ai/v1"
    assert config.llm.api_key_env == "MOONSHOT_API_KEY"
    assert config.llm.model == "kimi-k2.6"
    assert config.llm.stage_overrides["planner"].model is None
    assert config.llm.stage_overrides["executor"].model is None
    assert config.llm.stage_overrides["reconciler"].model is None


def test_load_config_accepts_openai_provider(tmp_path: Path) -> None:
    write_config(
        tmp_path,
        body=BASE_CONFIG.replace("provider: anthropic", "provider: openai").replace(
            "model: claude-sonnet-4-5",
            "model: gpt-5.2",
        ),
    )

    config = load_config(config_dir=tmp_path, env={})

    assert config.llm.provider == "openai"
    assert config.llm.model == "gpt-5.2"


def test_load_config_accepts_openai_compatible_provider(tmp_path: Path) -> None:
    write_config(
        tmp_path,
        body=BASE_CONFIG.replace(
            "provider: anthropic\n  model: claude-sonnet-4-5",
            """\
provider: openai_compatible
  base_url: https://api.moonshot.ai/v1
  api_key_env: MOONSHOT_API_KEY
  model: kimi-k2.6""",
        ),
    )

    config = load_config(config_dir=tmp_path, env={})

    assert config.llm.provider == "openai_compatible"
    assert config.llm.base_url == "https://api.moonshot.ai/v1"
    assert config.llm.api_key_env == "MOONSHOT_API_KEY"
    assert config.llm.model == "kimi-k2.6"


def test_load_config_rejects_incomplete_openai_compatible_provider(
    tmp_path: Path,
) -> None:
    write_config(
        tmp_path,
        body=BASE_CONFIG.replace("provider: anthropic", "provider: openai_compatible"),
    )

    with pytest.raises(ValidationError, match="base_url is required"):
        load_config(config_dir=tmp_path, env={})


def test_load_config_accepts_stage_model_overrides(tmp_path: Path) -> None:
    write_config(
        tmp_path,
        body=BASE_CONFIG.replace("provider: anthropic", "provider: openai").replace(
            "model: claude-sonnet-4-5",
            "model: gpt-5-mini",
        ).replace(
            "  temperature: 0.0\n",
            """\
  temperature: 0.0
  stage_overrides:
    executor:
      model: gpt-5.2
      reasoning_effort: high
    reconciler:
      model: gpt-5.2
      max_output_tokens: 4096
""",
        )
    )

    config = load_config(config_dir=tmp_path, env={})

    assert config.llm.model == "gpt-5-mini"
    assert config.llm.stage_overrides["executor"].model == "gpt-5.2"
    assert config.llm.stage_overrides["executor"].reasoning_effort == "high"
    assert config.llm.stage_overrides["reconciler"].max_output_tokens == 4096


def test_load_config_reads_dotenv_for_overrides_and_sdk_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_dir = tmp_path / "config"
    write_config(config_dir)
    (tmp_path / ".env").write_text(
        "MOONSHOT_API_KEY=dotenv-moonshot-key\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)

    config = load_config(config_dir=config_dir)

    assert config.llm.provider == "anthropic"
    assert os.environ["MOONSHOT_API_KEY"] == "dotenv-moonshot-key"


def test_load_config_keeps_process_env_ahead_of_dotenv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_dir = tmp_path / "config"
    write_config(config_dir)
    (tmp_path / ".env").write_text(
        "MOONSHOT_API_KEY=dotenv-moonshot-key\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MOONSHOT_API_KEY", "process-moonshot-key")

    config = load_config(config_dir=config_dir)

    assert config.llm.provider == "anthropic"
    assert os.environ["MOONSHOT_API_KEY"] == "process-moonshot-key"


def test_load_config_rejects_malformed_dotenv(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    write_config(config_dir)
    (tmp_path / ".env").write_text("not-valid\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="Invalid .env entry"):
        load_config(config_dir=config_dir)


def test_load_config_applies_default_local_then_env_precedence(tmp_path: Path) -> None:
    write_config(tmp_path)
    (tmp_path / "local.yaml").write_text(
        """\
llm:
  model: claude-opus-4-1
execution:
  max_chunk_concurrency: 8
""",
        encoding="utf-8",
    )

    config = load_config(
        config_dir=tmp_path,
        env={
            "VERITEXT_LOGGING__LEVEL": "DEBUG",
            "VERITEXT_CHUNKING__WINDOW_TOKENS": "2400",
        },
    )

    assert config.llm.model == "claude-opus-4-1"
    assert config.execution.max_chunk_concurrency == 8
    assert config.logging.level == "DEBUG"
    assert config.chunking.window_tokens == 2400
    assert config.chunking.overlap_tokens == 120


def test_load_config_rejects_malformed_yaml_and_unknown_keys(tmp_path: Path) -> None:
    write_config(tmp_path, body="not: [valid")

    with pytest.raises(ConfigError):
        load_config(config_dir=tmp_path, env={})

    write_config(tmp_path, body=BASE_CONFIG + "unexpected: true\n")

    with pytest.raises(ValidationError):
        load_config(config_dir=tmp_path, env={})


def test_chunking_config_rejects_overlap_that_consumes_window(tmp_path: Path) -> None:
    write_config(
        tmp_path,
        body=BASE_CONFIG.replace("overlap_tokens: 120", "overlap_tokens: 1200"),
    )

    with pytest.raises(ValidationError):
        load_config(config_dir=tmp_path, env={})


def test_run_context_propagates_across_async_tasks_and_resets() -> None:
    context = RunContext(
        run_id="run-1",
        doc_id="doc-1",
        audit_db_path=".veritext/run-1.sqlite3",
    )

    async def read_context_from_task() -> RunContext:
        return get_run_context()

    async def run_check() -> RunContext:
        with bind_run_context(context):
            return await asyncio.create_task(read_context_from_task())

    assert asyncio.run(run_check()) == context
    assert maybe_run_context() is None

    with pytest.raises(RuntimeError, match="No run context is bound"):
        get_run_context()


def test_configured_logging_emits_json_with_run_context() -> None:
    stream = StringIO()
    configure_logging(LoggingConfig(level="INFO", format="json"), stream=stream)
    context = RunContext(
        run_id="run-1",
        doc_id="doc-1",
        audit_db_path=".veritext/run-1.sqlite3",
    )

    with bind_run_context(context):
        structlog.get_logger("extractor.test").info(
            "candidate_rejected",
            reason="invented_span",
        )

    event = json.loads(stream.getvalue())

    assert event["event"] == "candidate_rejected"
    assert event["reason"] == "invented_span"
    assert event["run_id"] == "run-1"
    assert event["doc_id"] == "doc-1"
    assert event["audit_db_path"] == ".veritext/run-1.sqlite3"
    assert event["level"] == "info"
    assert event["logger"] == "extractor.test"
