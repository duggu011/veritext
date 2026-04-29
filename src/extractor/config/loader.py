from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from extractor.config.models import ExtractorConfig


ENV_PREFIX = "VERITEXT_"


class ConfigError(ValueError):
    """Raised when configuration files or environment overrides are malformed."""


def default_config_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "config"


def load_config(
    *,
    config_dir: Path | None = None,
    env: Mapping[str, str] | None = None,
    include_local: bool = True,
    include_env_file: bool = True,
    env_file: Path | None = None,
    env_prefix: str = ENV_PREFIX,
) -> ExtractorConfig:
    directory = config_dir or default_config_dir()
    raw_config = _read_yaml_mapping(directory / "default.yaml", required=True)

    local_path = directory / "local.yaml"
    if include_local and local_path.exists():
        raw_config = _deep_merge(raw_config, _read_yaml_mapping(local_path, required=True))

    runtime_env = _runtime_env(
        env=env,
        env_file=env_file or directory.parent / ".env",
        include_env_file=include_env_file,
    )
    raw_config = _deep_merge(raw_config, _env_overrides(runtime_env, env_prefix))
    return ExtractorConfig.model_validate(raw_config)


def _read_yaml_mapping(path: Path, *, required: bool) -> dict[str, Any]:
    if not path.exists():
        if required:
            raise ConfigError(f"Missing required configuration file: {path}")
        return {}

    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in configuration file: {path}") from exc

    if not isinstance(parsed, dict):
        raise ConfigError(f"Configuration file must contain a mapping: {path}")
    return parsed


def _env_overrides(env: Mapping[str, str], prefix: str) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    for name, value in sorted(env.items()):
        if not name.startswith(prefix):
            continue

        path = name.removeprefix(prefix).lower().split("__")
        if not path or any(part == "" for part in path):
            raise ConfigError(f"Invalid environment override name: {name}")

        node = overrides
        for part in path[:-1]:
            existing = node.setdefault(part, {})
            if not isinstance(existing, dict):
                raise ConfigError(f"Conflicting environment override path: {name}")
            node = existing

        leaf = path[-1]
        if leaf in node and isinstance(node[leaf], dict):
            raise ConfigError(f"Conflicting environment override path: {name}")
        node[leaf] = _parse_env_value(value)
    return overrides


def _runtime_env(
    *,
    env: Mapping[str, str] | None,
    env_file: Path,
    include_env_file: bool,
) -> Mapping[str, str]:
    if env is not None:
        return env

    dotenv_values = _read_dotenv_mapping(env_file) if include_env_file else {}
    for key, value in dotenv_values.items():
        os.environ.setdefault(key, value)
    return {**dotenv_values, **os.environ}


def _read_dotenv_mapping(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        if "=" not in line:
            raise ConfigError(f"Invalid .env entry at {path}:{line_number}")

        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key or any(character.isspace() for character in key):
            raise ConfigError(f"Invalid .env key at {path}:{line_number}")
        values[key] = _parse_dotenv_value(raw_value.strip())
    return values


def _parse_dotenv_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _parse_env_value(value: str) -> Any:
    try:
        return yaml.safe_load(value)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML scalar in environment override: {value}") from exc


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, Mapping) and isinstance(value, Mapping):
            merged[key] = _deep_merge(existing, value)
        else:
            merged[key] = value
    return merged


__all__ = ["ConfigError", "ENV_PREFIX", "default_config_dir", "load_config"]
