"""Evaluation fixtures and scoring harnesses."""

from extractor.evals.models import (
    CategoryMetricBreakdown,
    DataPointMatch,
    EvaluationCase,
    EvaluationMetrics,
    EvaluationResult,
    EvaluationThresholds,
    ExpectedDataPoint,
    FieldMetricBreakdown,
    InvariantViolation,
)
from extractor.evals.drops import (
    RunDropSummary,
    StageDropSummary,
    summarize_rejections,
    summarize_run_drops,
)
from extractor.evals.scoring import (
    EvaluationError,
    evaluate_report,
    evaluate_report_file,
    load_evaluation_case,
    load_extraction_report,
)

__all__ = [
    "CategoryMetricBreakdown",
    "DataPointMatch",
    "EvaluationCase",
    "EvaluationError",
    "EvaluationMetrics",
    "EvaluationResult",
    "EvaluationThresholds",
    "ExpectedDataPoint",
    "FieldMetricBreakdown",
    "InvariantViolation",
    "RunDropSummary",
    "StageDropSummary",
    "evaluate_report",
    "evaluate_report_file",
    "load_evaluation_case",
    "load_extraction_report",
    "summarize_rejections",
    "summarize_run_drops",
]
