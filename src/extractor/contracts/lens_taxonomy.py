from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from extractor.contracts.base import ContractModel, NonEmptyStr
from extractor.contracts.normalization import ValueKind


LensTaxonomyName = Literal[
    "entity",
    "event",
    "claim",
    "number",
    "relation",
    "definition",
    "citation",
    "temporal",
    "quantity_with_unit",
    "obligation",
    "condition",
    "exception",
]
LensRuntimeStatus = Literal["contract_only", "executable"]

EXECUTABLE_LENS_NAMES: frozenset[str] = frozenset(
    {"entity", "event", "claim", "number"}
)


class LensDefinition(ContractModel):
    name: LensTaxonomyName
    runtime_status: LensRuntimeStatus
    description: NonEmptyStr
    source_requirements: tuple[NonEmptyStr, ...] = Field(min_length=1)
    allowed_value_kinds: tuple[ValueKind, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_runtime_status(self) -> LensDefinition:
        if self.runtime_status == "executable" and self.name not in EXECUTABLE_LENS_NAMES:
            raise ValueError("planned-only lens cannot be executable in Phase 36")
        return self


class LensRegistry(ContractModel):
    definitions: tuple[LensDefinition, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_definitions(self) -> LensRegistry:
        names = [definition.name for definition in self.definitions]
        if len(names) != len(set(names)):
            raise ValueError("lens definitions must be unique by name")
        return self

    @property
    def executable_names(self) -> tuple[LensTaxonomyName, ...]:
        return tuple(
            definition.name
            for definition in self.definitions
            if definition.runtime_status == "executable"
        )

    @property
    def contract_only_names(self) -> tuple[LensTaxonomyName, ...]:
        return tuple(
            definition.name
            for definition in self.definitions
            if definition.runtime_status == "contract_only"
        )

    def definition_for(self, name: LensTaxonomyName) -> LensDefinition:
        for definition in self.definitions:
            if definition.name == name:
                return definition
        raise KeyError(name)


def default_lens_registry() -> LensRegistry:
    return LensRegistry(
        definitions=(
            LensDefinition(
                name="entity",
                runtime_status="executable",
                description="Named source-backed entities.",
                source_requirements=("exact source span",),
                allowed_value_kinds=("entity", "text"),
            ),
            LensDefinition(
                name="event",
                runtime_status="executable",
                description="Source-backed events or state changes.",
                source_requirements=("exact source span",),
                allowed_value_kinds=("text", "date", "datetime"),
            ),
            LensDefinition(
                name="claim",
                runtime_status="executable",
                description="Source-backed assertions or findings.",
                source_requirements=("exact source span",),
                allowed_value_kinds=("text",),
            ),
            LensDefinition(
                name="number",
                runtime_status="executable",
                description="Source-backed numeric facts.",
                source_requirements=("exact source span",),
                allowed_value_kinds=("number", "quantity", "text"),
            ),
            LensDefinition(
                name="relation",
                runtime_status="contract_only",
                description="Source-backed relationship between two or more facts.",
                source_requirements=("exact source span",),
                allowed_value_kinds=("text",),
            ),
            LensDefinition(
                name="definition",
                runtime_status="contract_only",
                description="Source-backed defined term or meaning.",
                source_requirements=("exact source span",),
                allowed_value_kinds=("text",),
            ),
            LensDefinition(
                name="citation",
                runtime_status="contract_only",
                description="Source-backed cross-reference or authority citation.",
                source_requirements=("exact source span",),
                allowed_value_kinds=("citation", "text"),
            ),
            LensDefinition(
                name="temporal",
                runtime_status="contract_only",
                description="Source-backed date, time, or duration fact.",
                source_requirements=("exact source span",),
                allowed_value_kinds=("date", "datetime", "duration", "text"),
            ),
            LensDefinition(
                name="quantity_with_unit",
                runtime_status="contract_only",
                description="Source-backed quantity with explicit unit and scope.",
                source_requirements=("exact source span",),
                allowed_value_kinds=("quantity", "number", "text"),
            ),
            LensDefinition(
                name="obligation",
                runtime_status="contract_only",
                description="Source-backed duty or required action.",
                source_requirements=("exact source span",),
                allowed_value_kinds=("text",),
            ),
            LensDefinition(
                name="condition",
                runtime_status="contract_only",
                description="Source-backed precondition or qualifier.",
                source_requirements=("exact source span",),
                allowed_value_kinds=("text", "boolean"),
            ),
            LensDefinition(
                name="exception",
                runtime_status="contract_only",
                description="Source-backed carve-out or exception.",
                source_requirements=("exact source span",),
                allowed_value_kinds=("text",),
            ),
        )
    )


__all__ = [
    "EXECUTABLE_LENS_NAMES",
    "LensDefinition",
    "LensRegistry",
    "LensRuntimeStatus",
    "LensTaxonomyName",
    "default_lens_registry",
]
