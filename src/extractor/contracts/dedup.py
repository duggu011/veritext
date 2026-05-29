from __future__ import annotations

from typing import Literal

from pydantic import Field

from extractor.contracts.base import ContractModel, NonEmptyStr, NonNegativeInt
from extractor.contracts.normalization import ValueKind


CanonicalValueSource = Literal["value", "value_verbatim", "value_canonical"]


class CanonicalValueKey(ContractModel):
    kind: ValueKind
    key: NonEmptyStr
    source: CanonicalValueSource
    policy_id: NonEmptyStr | None = None
    policy_version: NonEmptyStr | None = None


class DedupCluster(ContractModel):
    primary_candidate_id: NonEmptyStr
    merged_candidate_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    all_candidate_ids: tuple[NonEmptyStr, ...] = Field(min_length=2)
    canonical_key: CanonicalValueKey
    source_span_count: NonNegativeInt


__all__ = [
    "CanonicalValueKey",
    "CanonicalValueSource",
    "DedupCluster",
]
