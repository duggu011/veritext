from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Literal, Sequence

from pydantic import model_validator

from extractor.contracts.base import (
    ContractModel,
    LensName,
    NonEmptyStr,
    Sha256Hex,
)

if TYPE_CHECKING:
    from extractor.contracts.models import CategoryDefinition


SchemaSourceKind = Literal["planner_generated", "domain_pack_template"]
SCHEMA_HASH_PREFIX_LENGTH = 12


class DomainPackMetadata(ContractModel):
    pack_id: NonEmptyStr
    display_name: NonEmptyStr
    version: NonEmptyStr
    domain_hints: tuple[NonEmptyStr, ...]
    schema_template_ids: tuple[NonEmptyStr, ...]
    supported_document_classes: tuple[NonEmptyStr, ...]
    default_lenses: tuple[LensName, ...] = ()
    reporting_expectations: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_unique_metadata(self) -> DomainPackMetadata:
        if len(self.schema_template_ids) != len(set(self.schema_template_ids)):
            raise ValueError("schema template IDs must be unique")
        if len(self.default_lenses) != len(set(self.default_lenses)):
            raise ValueError("default lenses must be unique")
        return self


class SchemaTemplateMetadata(ContractModel):
    schema_id: NonEmptyStr
    schema_version: NonEmptyStr
    display_name: NonEmptyStr
    domain_pack_id: NonEmptyStr
    document_class: NonEmptyStr
    field_roles: tuple[NonEmptyStr, ...] = ()
    enabled_lenses: tuple[LensName, ...] = ()
    reporting_expectations: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_unique_lenses(self) -> SchemaTemplateMetadata:
        if len(self.enabled_lenses) != len(set(self.enabled_lenses)):
            raise ValueError("enabled lenses must be unique")
        return self


class ApprovedSchemaMetadata(ContractModel):
    schema_id: NonEmptyStr
    schema_version: NonEmptyStr
    schema_hash: Sha256Hex
    source_kind: SchemaSourceKind
    domain_pack_id: NonEmptyStr | None = None
    document_class: NonEmptyStr | None = None
    created_from: NonEmptyStr
    refined_from_schema_id: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_source_metadata(self) -> ApprovedSchemaMetadata:
        if self.source_kind == "domain_pack_template" and self.domain_pack_id is None:
            raise ValueError("domain_pack_template schemas require domain_pack_id")
        return self


def canonical_schema_hash(
    *,
    approved_categories: Sequence["CategoryDefinition"],
    source_kind: SchemaSourceKind,
    schema_version: str,
    domain_hints: Sequence[str] = (),
    domain_pack_id: str | None = None,
    document_class: str | None = None,
) -> str:
    if not approved_categories:
        raise ValueError("schema hash requires at least one approved category")

    canonical_payload = {
        "approved_categories": [
            _canonical_category(category)
            for category in sorted(approved_categories, key=lambda category: category.name)
        ],
        "document_class": document_class,
        "domain_hints": sorted(domain_hints),
        "domain_pack_id": domain_pack_id,
        "schema_version": schema_version,
        "source_kind": source_kind,
    }
    serialized = json.dumps(
        canonical_payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_planner_generated_schema_metadata(
    *,
    approved_categories: Sequence["CategoryDefinition"],
    schema_version: str = "1",
    domain_hints: Sequence[str] = (),
    document_class: str | None = None,
) -> ApprovedSchemaMetadata:
    schema_hash = canonical_schema_hash(
        approved_categories=approved_categories,
        source_kind="planner_generated",
        schema_version=schema_version,
        domain_hints=domain_hints,
        document_class=document_class,
    )
    return ApprovedSchemaMetadata(
        schema_id=f"schema:{schema_hash[:SCHEMA_HASH_PREFIX_LENGTH]}",
        schema_version=schema_version,
        schema_hash=schema_hash,
        source_kind="planner_generated",
        domain_pack_id=None,
        document_class=document_class,
        created_from="planner",
        refined_from_schema_id=None,
    )


def _canonical_category(category: "CategoryDefinition") -> dict[str, object]:
    return {
        "description": category.description,
        "fields": [
            {
                "description": field.description,
                "name": field.name,
                "required": field.required,
                "value_type": field.value_type,
            }
            for field in sorted(category.fields, key=lambda field: field.name)
        ],
        "name": category.name,
    }


__all__ = [
    "ApprovedSchemaMetadata",
    "DomainPackMetadata",
    "SchemaSourceKind",
    "SchemaTemplateMetadata",
    "build_planner_generated_schema_metadata",
    "canonical_schema_hash",
]
