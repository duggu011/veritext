from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]
Sha256Hex = Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
Confidence = Annotated[float, Field(strict=True, ge=0.0, le=1.0)]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
PositiveInt = Annotated[int, Field(strict=True, ge=1)]
Timestamp = Annotated[datetime, Field(strict=True)]

LensName = Literal["entity", "event", "claim", "number"]
RunStatus = Literal["created", "running", "completed", "failed", "refused"]
DocumentFormat = Literal["plain_text", "markdown", "pdf"]
LLMStage = Literal[
    "planner.classify_document",
    "planner.propose_schema",
    "planner.critique_schema",
    "planner.select_strategy",
    "planner.allocate_budget",
    "executor.entity",
    "executor.event",
    "executor.claim",
    "executor.number",
    "critic",
    "verifier",
    "reconciler",
]
RejectionReasonCode = Literal[
    "invalid_source_offsets",
    "invented_span",
    "category_not_approved",
    "critic_rejected",
    "verifier_rejected",
    "reconciler_rejected",
    "schema_violation",
    "ambiguous_source_span",
    "duplicate_candidate",
]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


__all__ = [
    "Confidence",
    "ContractModel",
    "DocumentFormat",
    "LLMStage",
    "LensName",
    "NonEmptyStr",
    "NonNegativeInt",
    "PositiveInt",
    "RejectionReasonCode",
    "RunStatus",
    "Sha256Hex",
    "Timestamp",
]
