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
from extractor.evals.suites import (
    CategoryThreshold,
    EvaluationSuiteFixture,
    EvaluationSuiteManifest,
    EvaluationSuiteThresholds,
    FieldThreshold,
    SuiteMetricThresholds,
    load_suite_manifest,
)

__all__ = [
    "CategoryMetricBreakdown",
    "CategoryThreshold",
    "DataPointMatch",
    "EvaluationCase",
    "EvaluationError",
    "EvaluationMetrics",
    "EvaluationResult",
    "EvaluationSuiteFixture",
    "EvaluationSuiteManifest",
    "EvaluationSuiteThresholds",
    "EvaluationThresholds",
    "ExpectedDataPoint",
    "FieldMetricBreakdown",
    "FieldThreshold",
    "InvariantViolation",
    "RunDropSummary",
    "StageDropSummary",
    "SuiteMetricThresholds",
    "evaluate_report",
    "evaluate_report_file",
    "load_evaluation_case",
    "load_extraction_report",
    "load_suite_manifest",
    "summarize_rejections",
    "summarize_run_drops",
]
