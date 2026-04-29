"""Evaluation fixtures and scoring harnesses."""

from extractor.evals.models import (
    DataPointMatch,
    EvaluationCase,
    EvaluationMetrics,
    EvaluationResult,
    EvaluationThresholds,
    ExpectedDataPoint,
    InvariantViolation,
)
from extractor.evals.scoring import (
    EvaluationError,
    evaluate_report,
    evaluate_report_file,
    load_evaluation_case,
    load_extraction_report,
)

__all__ = [
    "DataPointMatch",
    "EvaluationCase",
    "EvaluationError",
    "EvaluationMetrics",
    "EvaluationResult",
    "EvaluationThresholds",
    "ExpectedDataPoint",
    "InvariantViolation",
    "evaluate_report",
    "evaluate_report_file",
    "load_evaluation_case",
    "load_extraction_report",
]
