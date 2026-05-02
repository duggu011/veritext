"""Parallel extraction lens executors."""

from extractor.executor.models import (
    ExecutionResult,
    ExecutorCandidateBatch,
    ExecutorStageInput,
    ExecutorTaskResult,
    ExtractedCandidatePayload,
)
from extractor.executor.dedup import build_dedup_rejections, deduplicate_candidates
from extractor.executor.errors import ExecutorError
from extractor.executor.service import execute_plan

__all__ = [
    "build_dedup_rejections",
    "deduplicate_candidates",
    "ExecutionResult",
    "ExecutorCandidateBatch",
    "ExecutorError",
    "ExecutorStageInput",
    "ExecutorTaskResult",
    "ExtractedCandidatePayload",
    "execute_plan",
]
