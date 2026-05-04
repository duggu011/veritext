import pytest
from pydantic import ValidationError

from extractor.contracts import (
    ApprovedSchemaMetadata,
    CategoryDefinition,
    DomainPackMetadata,
    FieldDefinition,
    SchemaTemplateMetadata,
    build_planner_generated_schema_metadata,
    canonical_schema_hash,
)


def make_category(
    name: str = "Finding",
    description: str = "A source-backed finding.",
) -> CategoryDefinition:
    return CategoryDefinition(
        name=name,
        description=description,
        fields=(
            FieldDefinition(
                name="summary",
                description="Short extracted source text.",
                value_type="text",
                required=True,
            ),
            FieldDefinition(
                name="confidence_note",
                description="Source-backed confidence rationale.",
                value_type="text",
                required=False,
            ),
        ),
    )


def test_domain_pack_metadata_is_strict_and_requires_unique_schema_templates() -> None:
    pack = DomainPackMetadata(
        pack_id="generic-pack",
        display_name="Generic Pack",
        version="1.0.0",
        domain_hints=("generic", "metadata"),
        schema_template_ids=("template-alpha", "template-beta"),
        supported_document_classes=("generic_notice",),
        default_lenses=("claim", "entity"),
        reporting_expectations=("cite_schema_identity",),
    )

    assert pack.schema_template_ids == ("template-alpha", "template-beta")

    with pytest.raises(ValidationError, match="schema template IDs must be unique"):
        DomainPackMetadata(
            pack_id="generic-pack",
            display_name="Generic Pack",
            version="1.0.0",
            domain_hints=("generic",),
            schema_template_ids=("template-alpha", "template-alpha"),
            supported_document_classes=("generic_notice",),
        )

    with pytest.raises(ValidationError):
        DomainPackMetadata(
            pack_id="generic-pack",
            display_name="Generic Pack",
            version="1.0.0",
            domain_hints=("generic",),
            schema_template_ids=("template-alpha",),
            supported_document_classes=("generic_notice",),
            unexpected="not allowed",
        )


def test_schema_template_metadata_links_to_pack_and_rejects_duplicate_lenses() -> None:
    template = SchemaTemplateMetadata(
        schema_id="template-alpha",
        schema_version="1.0.0",
        display_name="Generic Notice Template",
        domain_pack_id="generic-pack",
        document_class="generic_notice",
        field_roles=("fact", "support"),
        enabled_lenses=("claim", "entity"),
        reporting_expectations=("cite_schema_identity",),
    )

    assert template.domain_pack_id == "generic-pack"

    with pytest.raises(ValidationError, match="enabled lenses must be unique"):
        SchemaTemplateMetadata(
            schema_id="template-alpha",
            schema_version="1.0.0",
            display_name="Generic Notice Template",
            domain_pack_id="generic-pack",
            document_class="generic_notice",
            field_roles=("fact",),
            enabled_lenses=("claim", "claim"),
        )


def test_approved_schema_metadata_enforces_source_kind_pack_rules() -> None:
    metadata = ApprovedSchemaMetadata(
        schema_id="schema:abcd1234efgh",
        schema_version="1",
        schema_hash="a" * 64,
        source_kind="planner_generated",
        domain_pack_id=None,
        document_class=None,
        created_from="planner",
        refined_from_schema_id=None,
    )

    assert metadata.source_kind == "planner_generated"

    with pytest.raises(ValidationError, match="domain_pack_template schemas require domain_pack_id"):
        ApprovedSchemaMetadata(
            schema_id="schema:abcd1234efgh",
            schema_version="1",
            schema_hash="a" * 64,
            source_kind="domain_pack_template",
            domain_pack_id=None,
            document_class="generic_notice",
            created_from="domain_pack",
            refined_from_schema_id=None,
        )


def test_canonical_schema_hash_is_sorted_and_deterministic() -> None:
    alpha = make_category("Alpha")
    beta = make_category("Beta")

    first = canonical_schema_hash(
        approved_categories=(beta, alpha),
        source_kind="planner_generated",
        schema_version="1",
        domain_hints=("metadata", "generic"),
        document_class="generic_notice",
    )
    second = canonical_schema_hash(
        approved_categories=(alpha, beta),
        source_kind="planner_generated",
        schema_version="1",
        domain_hints=("generic", "metadata"),
        document_class="generic_notice",
    )

    assert first == second
    assert len(first) == 64


def test_canonical_schema_hash_changes_when_field_semantics_change() -> None:
    original = make_category()
    changed = CategoryDefinition(
        name="Finding",
        description="A source-backed finding.",
        fields=(
            FieldDefinition(
                name="summary",
                description="Long extracted source text.",
                value_type="text",
                required=True,
            ),
            FieldDefinition(
                name="confidence_note",
                description="Source-backed confidence rationale.",
                value_type="text",
                required=False,
            ),
        ),
    )

    assert canonical_schema_hash(
        approved_categories=(original,),
        source_kind="planner_generated",
        schema_version="1",
    ) != canonical_schema_hash(
        approved_categories=(changed,),
        source_kind="planner_generated",
        schema_version="1",
    )


def test_planner_generated_schema_metadata_uses_hash_prefixed_schema_id() -> None:
    metadata = build_planner_generated_schema_metadata(
        approved_categories=(make_category(),),
        schema_version="1",
        domain_hints=("generic",),
        document_class="generic_notice",
    )

    assert metadata.schema_id == f"schema:{metadata.schema_hash[:12]}"
    assert metadata.source_kind == "planner_generated"
    assert metadata.domain_pack_id is None
