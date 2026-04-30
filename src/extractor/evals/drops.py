from __future__ import annotations

from collections import Counter
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from extractor.audit import AuditStore, CandidateRejection
from extractor.audit.models import RejectionStage


NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]


class StageDropSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    stage: RejectionStage
    total: NonNegativeInt
    by_code: dict[str, NonNegativeInt]


class RunDropSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    run_id: str
    total: NonNegativeInt
    stages: tuple[StageDropSummary, ...]


def summarize_rejections(
    rejections: tuple[CandidateRejection, ...],
    *,
    run_id: str,
) -> RunDropSummary:
    by_stage: dict[RejectionStage, Counter[str]] = {}
    total = 0
    for rejection in rejections:
        if rejection.run_id != run_id:
            continue
        codes = by_stage.setdefault(rejection.stage, Counter())
        for reason in rejection.reasons:
            codes[reason.code] += 1
        total += 1
    stages = tuple(
        StageDropSummary(
            stage=stage,
            total=sum(codes.values()),
            by_code=dict(codes),
        )
        for stage, codes in sorted(by_stage.items())
    )
    return RunDropSummary(run_id=run_id, total=total, stages=stages)


async def summarize_run_drops(audit_store: AuditStore, run_id: str) -> RunDropSummary:
    rejections = await audit_store.list_candidate_rejections_for_run(run_id)
    return summarize_rejections(rejections, run_id=run_id)


__all__ = [
    "RunDropSummary",
    "StageDropSummary",
    "summarize_rejections",
    "summarize_run_drops",
]
