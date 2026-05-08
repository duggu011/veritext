from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from extractor.contracts import PlanningRefusal, RejectionReason


NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]
Timestamp = Annotated[datetime, Field(strict=True)]
RejectionStage = Literal[
    "executor",
    "critic",
    "verifier",
    "reconciler",
    "schema",
    "dedup",
]
RunStageName = Literal[
    "ingestion",
    "chunker",
    "planner",
    "executor",
    "dedup",
    "critic",
    "verifier",
    "reconciler",
    "reporter",
]


class AuditModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CandidateRejection(AuditModel):
    rejection_id: NonEmptyStr
    run_id: NonEmptyStr
    candidate_id: NonEmptyStr
    stage: RejectionStage
    reasons: tuple[RejectionReason, ...] = Field(min_length=1)
    created_at: Timestamp


class RunStageState(AuditModel):
    run_id: NonEmptyStr
    stage: RunStageName
    completed_at: Timestamp
    planning_refusal: PlanningRefusal | None = None

    @model_validator(mode="after")
    def validate_planner_refusal(self) -> RunStageState:
        if self.planning_refusal is None:
            return self
        if self.stage != "planner":
            raise ValueError("planning_refusal can only be attached to planner stage state")
        if self.planning_refusal.run_id != self.run_id:
            raise ValueError("planning_refusal run_id must match stage state run_id")
        return self


__all__ = [
    "CandidateRejection",
    "RejectionStage",
    "RunStageName",
    "RunStageState",
]
