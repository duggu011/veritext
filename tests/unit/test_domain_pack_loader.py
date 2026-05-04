from pathlib import Path

import pytest

from extractor.planner.domain_packs import (
    DomainPackLoaderError,
    load_domain_pack_artifacts,
)


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "domain_packs"


def test_load_domain_pack_artifacts_validates_synthetic_yaml_fixture() -> None:
    artifacts = load_domain_pack_artifacts(FIXTURES)

    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact.path == FIXTURES / "generic_metadata_pack.yaml"
    assert artifact.metadata.pack_id == "generic-metadata-pack"
    assert artifact.metadata.schema_template_ids == ("generic-notice-template",)
    assert artifact.schema_templates[0].schema_id == "generic-notice-template"
    assert artifact.schema_templates[0].domain_pack_id == "generic-metadata-pack"


def test_load_domain_pack_artifacts_returns_empty_for_missing_directory(
    tmp_path: Path,
) -> None:
    assert load_domain_pack_artifacts(tmp_path / "missing") == ()


def test_load_domain_pack_artifacts_rejects_template_id_drift(tmp_path: Path) -> None:
    packs_dir = tmp_path / "packs"
    packs_dir.mkdir()
    (packs_dir / "bad.yaml").write_text(
        """\
metadata:
  pack_id: generic-metadata-pack
  display_name: Generic Metadata Pack
  version: 1.0.0
  domain_hints: [generic]
  schema_template_ids: [expected-template]
  supported_document_classes: [generic_notice]
schema_templates:
  - schema_id: actual-template
    schema_version: 1.0.0
    display_name: Actual Template
    domain_pack_id: generic-metadata-pack
    document_class: generic_notice
""",
        encoding="utf-8",
    )

    with pytest.raises(DomainPackLoaderError, match="schema_template_ids must match"):
        load_domain_pack_artifacts(packs_dir)


def test_load_domain_pack_artifacts_rejects_non_yaml_artifacts(tmp_path: Path) -> None:
    packs_dir = tmp_path / "packs"
    packs_dir.mkdir()
    (packs_dir / "bad.json").write_text("{}", encoding="utf-8")

    with pytest.raises(DomainPackLoaderError, match="YAML artifacts only"):
        load_domain_pack_artifacts(packs_dir)
