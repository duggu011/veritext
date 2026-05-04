from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError, model_validator

from extractor.contracts import DomainPackMetadata, SchemaTemplateMetadata
from extractor.contracts.base import ContractModel


class DomainPackLoaderError(ValueError):
    """Raised when a configured domain-pack artifact is malformed."""


class DomainPackArtifact(ContractModel):
    path: Path
    metadata: DomainPackMetadata
    schema_templates: tuple[SchemaTemplateMetadata, ...]

    @model_validator(mode="after")
    def validate_template_metadata(self) -> DomainPackArtifact:
        template_ids = tuple(template.schema_id for template in self.schema_templates)
        if len(template_ids) != len(set(template_ids)):
            raise ValueError("schema template IDs must be unique within artifact")
        if set(template_ids) != set(self.metadata.schema_template_ids):
            raise ValueError("schema_template_ids must match schema_templates")

        for template in self.schema_templates:
            if template.domain_pack_id != self.metadata.pack_id:
                raise ValueError("schema template domain_pack_id must match pack_id")
        return self


def load_domain_pack_artifacts(directory: Path) -> tuple[DomainPackArtifact, ...]:
    if not directory.exists():
        return ()
    if not directory.is_dir():
        raise DomainPackLoaderError(f"Domain pack path is not a directory: {directory}")

    artifacts: list[DomainPackArtifact] = []
    for path in sorted(item for item in directory.iterdir() if item.is_file()):
        if path.name.startswith("."):
            continue
        if path.suffix not in {".yaml", ".yml"}:
            raise DomainPackLoaderError(f"Domain pack directory accepts YAML artifacts only: {path}")
        artifacts.append(_load_domain_pack_artifact(path))
    return tuple(artifacts)


def _load_domain_pack_artifact(path: Path) -> DomainPackArtifact:
    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise DomainPackLoaderError(f"Invalid YAML in domain-pack artifact: {path}") from exc

    if not isinstance(parsed, dict):
        raise DomainPackLoaderError(f"Domain-pack artifact must contain a mapping: {path}")

    try:
        return DomainPackArtifact.model_validate({"path": path, **parsed})
    except ValidationError as exc:
        raise DomainPackLoaderError(f"Invalid domain-pack artifact {path}: {exc}") from exc


__all__ = [
    "DomainPackArtifact",
    "DomainPackLoaderError",
    "load_domain_pack_artifacts",
]
