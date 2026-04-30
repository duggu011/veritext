from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from extractor.contracts import RejectionReason


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


__all__ = [
    "CandidateRejection",
    "RejectionStage",
    "RunStageName",
    "RunStageState",
]
