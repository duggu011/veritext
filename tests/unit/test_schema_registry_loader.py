from pathlib import Path

import pytest

from extractor.contracts import (
    CategoryDefinition,
    FieldDefinition,
    canonical_schema_hash,
)
from extractor.planner.schema_registry import (
    SchemaRegistryLoaderError,
    load_schema_registry_artifacts,
    select_schema_registry_candidates,
)


def make_category(name: str = "Finding") -> CategoryDefinition:
    return CategoryDefinition(
        name=name,
        description="A source-backed finding.",
        fields=(
            FieldDefinition(
                name="summary",
                description="Short extracted source text.",
                value_type="text",
                required=True,
            ),
        ),
    )


def write_registry_artifact(
    directory: Path,
    *,
    filename: str = "generic_finding.yaml",
    schema_id: str = "schema:generic-finding-v1",
    schema_hash: str | None = None,
    document_class: str = "generic_notice",
    domain_hints: tuple[str, ...] = ("generic",),
) -> Path:
    category = make_category()
    resolved_hash = schema_hash or canonical_schema_hash(
        approved_categories=(category,),
        source_kind="schema_registry",
        schema_version="1.0.0",
        domain_hints=domain_hints,
        document_class=document_class,
    )
    path = directory / filename
    path.write_text(
        f"""\
schema_metadata:
  schema_id: {schema_id}
  schema_version: 1.0.0
  schema_hash: {resolved_hash}
  source_kind: schema_registry
  document_class: {document_class}
  created_from: schema_registry
approved_categories:
  - name: {category.name}
    description: {category.description}
    fields:
      - name: {category.fields[0].name}
        description: {category.fields[0].description}
        value_type: {category.fields[0].value_type}
        required: true
document_class: {document_class}
domain_hints: [{", ".join(domain_hints)}]
match_basis: [document_class, domain_hints]
""",
        encoding="utf-8",
    )
    return path


def test_load_schema_registry_artifacts_validates_yaml_and_hash(tmp_path: Path) -> None:
    registry_dir = tmp_path / "schema_registry"
    registry_dir.mkdir()
    write_registry_artifact(registry_dir)

    artifacts = load_schema_registry_artifacts(registry_dir)

    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact.schema_id == "schema:generic-finding-v1"
    assert artifact.schema_metadata.source_kind == "schema_registry"
    assert artifact.document_class == "generic_notice"
    assert artifact.approved_categories[0].name == "Finding"


def test_load_schema_registry_artifacts_returns_empty_for_missing_directory(
    tmp_path: Path,
) -> None:
    assert load_schema_registry_artifacts(tmp_path / "missing") == ()


def test_load_schema_registry_artifacts_rejects_non_directory(tmp_path: Path) -> None:
    registry_path = tmp_path / "schema_registry"
    registry_path.write_text("", encoding="utf-8")

    with pytest.raises(SchemaRegistryLoaderError, match="not a directory"):
        load_schema_registry_artifacts(registry_path)


def test_load_schema_registry_artifacts_rejects_non_yaml_artifacts(tmp_path: Path) -> None:
    registry_dir = tmp_path / "schema_registry"
    registry_dir.mkdir()
    (registry_dir / "bad.json").write_text("{}", encoding="utf-8")

    with pytest.raises(SchemaRegistryLoaderError, match="YAML artifacts only"):
        load_schema_registry_artifacts(registry_dir)


def test_load_schema_registry_artifacts_rejects_nested_directories(tmp_path: Path) -> None:
    registry_dir = tmp_path / "schema_registry"
    registry_dir.mkdir()
    (registry_dir / "nested").mkdir()

    with pytest.raises(SchemaRegistryLoaderError, match="YAML artifact files only"):
        load_schema_registry_artifacts(registry_dir)


def test_load_schema_registry_artifacts_rejects_malformed_yaml(tmp_path: Path) -> None:
    registry_dir = tmp_path / "schema_registry"
    registry_dir.mkdir()
    (registry_dir / "bad.yaml").write_text("schema_metadata: [", encoding="utf-8")

    with pytest.raises(SchemaRegistryLoaderError, match="Invalid YAML"):
        load_schema_registry_artifacts(registry_dir)


def test_load_schema_registry_artifacts_rejects_non_mapping_yaml(tmp_path: Path) -> None:
    registry_dir = tmp_path / "schema_registry"
    registry_dir.mkdir()
    (registry_dir / "bad.yaml").write_text("- not\n- a\n- mapping\n", encoding="utf-8")

    with pytest.raises(SchemaRegistryLoaderError, match="must contain a mapping"):
        load_schema_registry_artifacts(registry_dir)


def test_load_schema_registry_artifacts_rejects_hash_mismatch(tmp_path: Path) -> None:
    registry_dir = tmp_path / "schema_registry"
    registry_dir.mkdir()
    write_registry_artifact(registry_dir, schema_hash="b" * 64)

    with pytest.raises(SchemaRegistryLoaderError, match="schema_hash must match"):
        load_schema_registry_artifacts(registry_dir)


def test_load_schema_registry_artifacts_rejects_duplicate_schema_ids(tmp_path: Path) -> None:
    registry_dir = tmp_path / "schema_registry"
    registry_dir.mkdir()
    write_registry_artifact(registry_dir, filename="one.yaml")
    write_registry_artifact(registry_dir, filename="two.yaml")

    with pytest.raises(SchemaRegistryLoaderError, match="duplicate schema_id"):
        load_schema_registry_artifacts(registry_dir)


def test_select_schema_registry_candidates_matches_class_and_domain_hints(
    tmp_path: Path,
) -> None:
    registry_dir = tmp_path / "schema_registry"
    registry_dir.mkdir()
    write_registry_artifact(
        registry_dir,
        filename="financial.yaml",
        schema_id="schema:financial-v1",
        document_class="financial_update",
        domain_hints=("finance",),
    )
    write_registry_artifact(
        registry_dir,
        filename="policy.yaml",
        schema_id="schema:policy-v1",
        document_class="policy_notice",
        domain_hints=("policy",),
    )
    write_registry_artifact(
        registry_dir,
        filename="specific.yaml",
        schema_id="schema:specific-v1",
        document_class="financial_update",
        domain_hints=("finance", "quarterly"),
    )
    artifacts = load_schema_registry_artifacts(registry_dir)

    candidates = select_schema_registry_candidates(
        artifacts,
        document_class="financial_update",
        domain_hints=("finance", "user_hint"),
    )

    assert tuple(artifact.schema_id for artifact in candidates) == ("schema:financial-v1",)
