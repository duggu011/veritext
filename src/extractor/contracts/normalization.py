from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from extractor.contracts.base import ContractModel, NonEmptyStr


ValueKind = Literal[
    "text",
    "number",
    "date",
    "datetime",
    "duration",
    "quantity",
    "entity",
    "citation",
    "boolean",
]
NormalizationMode = Literal[
    "none",
    "verbatim",
    "source_traced_label",
    "number",
    "date",
    "datetime",
    "duration",
    "quantity",
    "entity_key",
    "citation_key",
    "boolean",
]
NormalizationStatus = Literal[
    "not_normalized",
    "verbatim_only",
    "canonicalized",
    "unsupported",
]


class NormalizationPolicy(ContractModel):
    policy_id: NonEmptyStr
    version: NonEmptyStr
    mode: NormalizationMode
    input_kind: ValueKind
    output_kind: ValueKind
    description: NonEmptyStr


class FieldNormalizationPolicy(ContractModel):
    category_name: NonEmptyStr
    field_name: NonEmptyStr
    value_kind: ValueKind
    policy_id: NonEmptyStr
    reject_unsupported: bool = Field(default=True, strict=True)


class NormalizationPolicyRegistry(ContractModel):
    policies: tuple[NormalizationPolicy, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_policy_versions(self) -> NormalizationPolicyRegistry:
        keys = [(policy.policy_id, policy.version) for policy in self.policies]
        if len(keys) != len(set(keys)):
            raise ValueError("normalization policies must be unique by policy_id and version")
        return self

    @property
    def policy_ids(self) -> tuple[str, ...]:
        return tuple(f"{policy.policy_id}@{policy.version}" for policy in self.policies)


def validate_normalization_metadata(
    *,
    value: str,
    value_verbatim: str | None,
    value_canonical: str | None,
    normalization_status: NormalizationStatus,
    normalization_policy_id: str | None,
    normalization_policy_version: str | None,
    normalization_notes: str | None,
) -> None:
    if normalization_status == "canonicalized":
        missing = [
            name
            for name, actual in (
                ("value_verbatim", value_verbatim),
                ("value_canonical", value_canonical),
                ("normalization_policy_id", normalization_policy_id),
                ("normalization_policy_version", normalization_policy_version),
            )
            if actual is None
        ]
        if missing:
            raise ValueError(
                "canonicalized normalization requires " + ", ".join(missing)
            )
        if value != value_canonical:
            raise ValueError("value must equal value_canonical when canonicalized")
        return

    if normalization_status == "verbatim_only":
        if value_verbatim is None:
            raise ValueError("verbatim_only normalization requires value_verbatim")
        if value_canonical is not None:
            raise ValueError("verbatim_only normalization must not include value_canonical")
        if value != value_verbatim:
            raise ValueError("value must equal value_verbatim when verbatim_only")
        return

    if normalization_status == "unsupported":
        if normalization_notes is None:
            raise ValueError("unsupported normalization requires normalization_notes")
        if value_canonical is not None:
            raise ValueError("unsupported normalization must not include value_canonical")
        return

    if value_canonical is not None:
        raise ValueError("not_normalized values must not include value_canonical")


__all__ = [
    "FieldNormalizationPolicy",
    "NormalizationMode",
    "NormalizationPolicy",
    "NormalizationPolicyRegistry",
    "NormalizationStatus",
    "ValueKind",
    "validate_normalization_metadata",
]
