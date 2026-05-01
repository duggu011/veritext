from __future__ import annotations

import json
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from extractor.audit import CandidateRejection
from extractor.contracts import (
    DataPoint,
    RejectionReason,
)
from extractor.contracts.models import RejectionReasonCode
from extractor.llm.views import LLMCandidateView, LLMSchemaCard


NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]
Confidence = Annotated[float, Field(strict=True, ge=0.0, le=1.0)]


class ReconcilerModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReconcilerStageInput(ReconcilerModel):
    schema_card: LLMSchemaCard
    candidates: tuple[LLMCandidateView, ...] = Field(min_length=1)


class ReconciledDataPointPayload(ReconcilerModel):
    category: NonEmptyStr
    field_name: NonEmptyStr
    value: NonEmptyStr
    source_candidate_id: NonEmptyStr
    contributing_candidate_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    confidence: Confidence

    @model_validator(mode="after")
    def validate_source_contributes(self) -> ReconciledDataPointPayload:
        if self.source_candidate_id not in self.contributing_candidate_ids:
            raise ValueError("source_candidate_id must be one of contributing_candidate_ids")
        if len(self.contributing_candidate_ids) != len(set(self.contributing_candidate_ids)):
            raise ValueError("contributing_candidate_ids must be unique")
        return self


class RejectedCandidatePayload(ReconcilerModel):
    candidate_id: NonEmptyStr
    reasons: tuple[RejectionReason, ...] = Field(min_length=1)


ReconciledGroupPayload = tuple[NonEmptyStr, tuple[NonEmptyStr, ...]]
RejectedCandidateDecision = tuple[NonEmptyStr, RejectionReasonCode]


class ReconciliationBatch(ReconcilerModel):
    groups: tuple[ReconciledGroupPayload, ...]
    rejected: tuple[RejectedCandidateDecision, ...]

    @model_validator(mode="before")
    @classmethod
    def _coerce_stringified_payload(cls, data: object) -> object:
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return data
        if isinstance(data, dict):
            coerced = dict(data)
            for field_name in ("groups", "rejected"):
                value = coerced.get(field_name)
                if isinstance(value, str):
                    try:
                        coerced[field_name] = json.loads(value)
                    except json.JSONDecodeError:
                        pass
            coerced["groups"] = _normalize_groups(coerced.get("groups"))
            coerced["rejected"] = _normalize_rejected(coerced.get("rejected"))
            return coerced
        return data

    @model_validator(mode="after")
    def validate_groups(self) -> ReconciliationBatch:
        for source_candidate_id, contributing_candidate_ids in self.groups:
            if source_candidate_id not in contributing_candidate_ids:
                raise ValueError(
                    "group source_candidate_id must be one of contributing_candidate_ids"
                )
            if len(contributing_candidate_ids) != len(set(contributing_candidate_ids)):
                raise ValueError("group contributing_candidate_ids must be unique")
        rejected_ids = [candidate_id for candidate_id, _ in self.rejected]
        if len(rejected_ids) != len(set(rejected_ids)):
            raise ValueError("rejected candidate IDs must be unique")
        return self


class ReconciliationResult(ReconcilerModel):
    data_points: tuple[DataPoint, ...]
    rejections: tuple[CandidateRejection, ...]


def _normalize_groups(value: object) -> object:
    if not isinstance(value, (list, tuple)):
        return value
    groups: list[object] = []
    for group in value:
        if isinstance(group, (list, tuple)) and len(group) == 2:
            source_candidate_id, contributing_candidate_ids = group
            if isinstance(contributing_candidate_ids, str):
                group = (source_candidate_id, (contributing_candidate_ids,))
        groups.append(group)
    return tuple(groups)


def _normalize_rejected(value: object) -> object:
    if not isinstance(value, (list, tuple)):
        return value
    rejected: list[object] = []
    for item in value:
        if isinstance(item, str):
            item = (item, "reconciler_rejected")
        elif isinstance(item, (list, tuple)) and len(item) == 1:
            item = (item[0], "reconciler_rejected")
        rejected.append(item)
    return tuple(rejected)


__all__ = [
    "ReconciledGroupPayload",
    "ReconciledDataPointPayload",
    "ReconciliationBatch",
    "ReconciliationResult",
    "ReconcilerStageInput",
    "RejectedCandidateDecision",
    "RejectedCandidatePayload",
]
