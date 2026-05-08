from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from extractor.contracts import ApprovedSchemaArtifact


class SchemaRegistryLoaderError(ValueError):
    """Raised when a configured approved-schema registry artifact is malformed."""


def load_schema_registry_artifacts(directory: Path) -> tuple[ApprovedSchemaArtifact, ...]:
    if not directory.exists():
        return ()
    if not directory.is_dir():
        raise SchemaRegistryLoaderError(f"Schema registry path is not a directory: {directory}")

    artifacts: list[ApprovedSchemaArtifact] = []
    seen_schema_paths: dict[str, Path] = {}
    for path in sorted(directory.iterdir()):
        if path.name.startswith("."):
            continue
        if not path.is_file():
            raise SchemaRegistryLoaderError(
                f"Schema registry directory accepts YAML artifact files only: {path}"
            )
        if path.suffix not in {".yaml", ".yml"}:
            raise SchemaRegistryLoaderError(
                f"Schema registry directory accepts YAML artifacts only: {path}"
            )

        artifact = _load_schema_registry_artifact(path)
        previous_path = seen_schema_paths.get(artifact.schema_id)
        if previous_path is not None:
            raise SchemaRegistryLoaderError(
                "duplicate schema_id in schema registry: "
                f"{artifact.schema_id} ({previous_path}, {path})"
            )
        seen_schema_paths[artifact.schema_id] = path
        artifacts.append(artifact)

    return tuple(artifacts)


def _load_schema_registry_artifact(path: Path) -> ApprovedSchemaArtifact:
    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise SchemaRegistryLoaderError(f"Invalid YAML in schema-registry artifact: {path}") from exc

    if not isinstance(parsed, dict):
        raise SchemaRegistryLoaderError(f"Schema-registry artifact must contain a mapping: {path}")

    try:
        return ApprovedSchemaArtifact.model_validate(parsed)
    except ValidationError as exc:
        raise SchemaRegistryLoaderError(f"Invalid schema-registry artifact {path}: {exc}") from exc


__all__ = [
    "SchemaRegistryLoaderError",
    "load_schema_registry_artifacts",
]
