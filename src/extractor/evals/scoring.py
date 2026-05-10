from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import ValidationError

from extractor.contracts import DataPoint
from extractor.evals.models import (
    CategoryMetricBreakdown,
    DataPointMatch,
    EvaluationCase,
    EvaluationMetrics,
    EvaluationResult,
    ExpectedDataPoint,
    FieldMetricBreakdown,
    InvariantViolation,
)
from extractor.reporter import ExtractionReport


class EvaluationError(RuntimeError):
    """Raised when an evaluation fixture or report cannot be scored safely."""


def load_evaluation_case(case_path: str | Path) -> EvaluationCase:
    path = Path(case_path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluationError(f"Failed to read evaluation case: {path}") from exc

    source_path_value = raw.get("source_path")
    if not isinstance(source_path_value, str) or not source_path_value.strip():
        raise EvaluationError("Evaluation case must include a non-empty source_path")

    source_path = Path(source_path_value)
    if not source_path.is_absolute():
        source_path = path.parent / source_path
    try:
        source_bytes = source_path.read_bytes()
        source_text = source_bytes.decode("utf-8")
    except OSError as exc:
        raise EvaluationError(f"Failed to read evaluation source: {source_path}") from exc
    except UnicodeDecodeError as exc:
        raise EvaluationError(f"Evaluation source must be UTF-8 text: {source_path}") from exc

    raw["source_path"] = str(source_path)
    raw["source_sha256"] = hashlib.sha256(source_bytes).hexdigest()
    raw["source_text"] = source_text
    try:
        return EvaluationCase.model_validate(raw)
    except ValidationError as exc:
        raise EvaluationError(f"Invalid evaluation case: {path}") from exc


def load_extraction_report(report_path: str | Path) -> ExtractionReport:
    path = Path(report_path)
    try:
        return ExtractionReport.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise EvaluationError(f"Invalid extraction report: {path}") from exc


def evaluate_report_file(case_path: str | Path, report_path: str | Path) -> EvaluationResult:
    return evaluate_report(load_evaluation_case(case_path), load_extraction_report(report_path))


def evaluate_report(case: EvaluationCase, report: ExtractionReport) -> EvaluationResult:
    invariant_violations = _report_invariant_violations(case, report)
    matches, missing_expected_ids, unexpected_data_point_ids = _match_data_points(
        expected=case.expected_data_points,
        actual=report.data_points,
    )
    exact_provenance_matches = sum(1 for match in matches if match.exact_provenance)
    metrics = _build_metrics(
        expected_count=len(case.expected_data_points),
        actual_count=len(report.data_points),
        true_positives=len(matches),
        exact_provenance_matches=exact_provenance_matches,
        invariant_violation_count=len(invariant_violations),
    )
    category_metrics = _build_category_metric_breakdowns(
        expected=case.expected_data_points,
        actual=report.data_points,
        matches=matches,
    )
    field_metrics = _build_field_metric_breakdowns(
        expected=case.expected_data_points,
        actual=report.data_points,
        matches=matches,
    )
    thresholds = case.thresholds
    passed = (
        metrics.precision >= thresholds.min_precision
        and metrics.recall >= thresholds.min_recall
        and metrics.f1 >= thresholds.min_f1
        and metrics.provenance_recall >= thresholds.min_provenance_recall
        and metrics.invariant_violation_count <= thresholds.max_invariant_violations
    )
    return EvaluationResult(
        case_id=case.case_id,
        run_id=report.run_id,
        doc_id=report.doc_id,
        metrics=metrics,
        category_metrics=tuple(category_metrics),
        field_metrics=tuple(field_metrics),
        matches=tuple(matches),
        missing_expected_ids=tuple(missing_expected_ids),
        unexpected_data_point_ids=tuple(unexpected_data_point_ids),
        invariant_violations=tuple(invariant_violations),
        passed=passed,
    )


def _build_category_metric_breakdowns(
    *,
    expected: tuple[ExpectedDataPoint, ...],
    actual: tuple[DataPoint, ...],
    matches: list[DataPointMatch],
) -> list[CategoryMetricBreakdown]:
    expected_by_id = {point.expected_id: point for point in expected}
    used_actual_ids = {match.data_point_id for match in matches}

    categories = {
        point.category for point in expected
    } | {
        point.category for point in actual if point.data_point_id not in used_actual_ids
    }

    breakdowns: list[CategoryMetricBreakdown] = []
    for category in sorted(categories):
        true_positive_matches = [
            match
            for match in matches
            if expected_by_id[match.expected_id].category == category
        ]
        false_positive_count = sum(
            1
            for point in actual
            if point.data_point_id not in used_actual_ids and point.category == category
        )
        metrics = _build_metrics(
            expected_count=sum(1 for point in expected if point.category == category),
            actual_count=len(true_positive_matches) + false_positive_count,
            true_positives=len(true_positive_matches),
            exact_provenance_matches=sum(
                1 for match in true_positive_matches if match.exact_provenance
            ),
            invariant_violation_count=0,
        )
        breakdowns.append(CategoryMetricBreakdown(category=category, metrics=metrics))
    return breakdowns


def _build_field_metric_breakdowns(
    *,
    expected: tuple[ExpectedDataPoint, ...],
    actual: tuple[DataPoint, ...],
    matches: list[DataPointMatch],
) -> list[FieldMetricBreakdown]:
    expected_by_id = {point.expected_id: point for point in expected}
    used_actual_ids = {match.data_point_id for match in matches}

    fields = {
        (point.category, point.field_name) for point in expected
    } | {
        (point.category, point.field_name)
        for point in actual
        if point.data_point_id not in used_actual_ids
    }

    breakdowns: list[FieldMetricBreakdown] = []
    for category, field_name in sorted(fields):
        true_positive_matches = [
            match
            for match in matches
            if (
                expected_by_id[match.expected_id].category,
                expected_by_id[match.expected_id].field_name,
            )
            == (category, field_name)
        ]
        false_positive_count = sum(
            1
            for point in actual
            if point.data_point_id not in used_actual_ids
            and (point.category, point.field_name) == (category, field_name)
        )
        metrics = _build_metrics(
            expected_count=sum(
                1
                for point in expected
                if (point.category, point.field_name) == (category, field_name)
            ),
            actual_count=len(true_positive_matches) + false_positive_count,
            true_positives=len(true_positive_matches),
            exact_provenance_matches=sum(
                1 for match in true_positive_matches if match.exact_provenance
            ),
            invariant_violation_count=0,
        )
        breakdowns.append(
            FieldMetricBreakdown(
                category=category,
                field_name=field_name,
                metrics=metrics,
            )
        )
    return breakdowns


def _build_metrics(
    *,
    expected_count: int,
    actual_count: int,
    true_positives: int,
    exact_provenance_matches: int,
    invariant_violation_count: int,
) -> EvaluationMetrics:
    false_positives = actual_count - true_positives
    false_negatives = expected_count - true_positives
    precision = true_positives / actual_count if actual_count else 0.0
    recall = true_positives / expected_count if expected_count else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    provenance_recall = (
        exact_provenance_matches / expected_count if expected_count else 1.0
    )
    return EvaluationMetrics(
        expected_count=expected_count,
        actual_count=actual_count,
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1=f1,
        exact_provenance_matches=exact_provenance_matches,
        provenance_recall=provenance_recall,
        invariant_violation_count=invariant_violation_count,
    )


def _match_data_points(
    *,
    expected: tuple[ExpectedDataPoint, ...],
    actual: tuple[DataPoint, ...],
) -> tuple[list[DataPointMatch], list[str], list[str]]:
    matches: list[DataPointMatch] = []
    used_expected: set[str] = set()
    used_actual: set[str] = set()

    for exact_only in (True, False):
        for expected_point in expected:
            if expected_point.expected_id in used_expected:
                continue
            for data_point in actual:
                if data_point.data_point_id in used_actual:
                    continue
                if _match_key(expected_point) != _actual_key(data_point):
                    continue
                exact_provenance = _exact_provenance_match(expected_point, data_point)
                if exact_only and not exact_provenance:
                    continue
                matches.append(
                    DataPointMatch(
                        expected_id=expected_point.expected_id,
                        data_point_id=data_point.data_point_id,
                        exact_provenance=exact_provenance,
                    )
                )
                used_expected.add(expected_point.expected_id)
                used_actual.add(data_point.data_point_id)
                break

    missing_expected_ids = [
        expected_point.expected_id
        for expected_point in expected
        if expected_point.expected_id not in used_expected
    ]
    unexpected_data_point_ids = [
        data_point.data_point_id
        for data_point in actual
        if data_point.data_point_id not in used_actual
    ]
    return matches, missing_expected_ids, unexpected_data_point_ids


def _report_invariant_violations(
    case: EvaluationCase,
    report: ExtractionReport,
) -> list[InvariantViolation]:
    violations: list[InvariantViolation] = []
    source_bytes = case.source_text.encode("utf-8")
    for data_point in report.data_points:
        span = data_point.source_span
        if span.end_char > len(case.source_text) or span.end_byte > len(source_bytes):
            violations.append(
                InvariantViolation(
                    code="source_span_out_of_bounds",
                    message="Data point source span exceeds the evaluation source text.",
                    data_point_id=data_point.data_point_id,
                )
            )
            continue

        expected_start_byte = len(case.source_text[: span.start_char].encode("utf-8"))
        expected_end_byte = len(case.source_text[: span.end_char].encode("utf-8"))
        if span.start_byte != expected_start_byte or span.end_byte != expected_end_byte:
            violations.append(
                InvariantViolation(
                    code="source_span_byte_offset_mismatch",
                    message="Data point byte offsets are not aligned to character offsets.",
                    data_point_id=data_point.data_point_id,
                )
            )

        if case.source_text[span.start_char : span.end_char] != span.text:
            violations.append(
                InvariantViolation(
                    code="source_span_text_mismatch",
                    message="Data point source_span.text does not match source text at offsets.",
                    data_point_id=data_point.data_point_id,
                )
            )
        if source_bytes[span.start_byte : span.end_byte] != span.text.encode("utf-8"):
            violations.append(
                InvariantViolation(
                    code="source_span_byte_mismatch",
                    message="Data point source_span.text does not match source bytes at offsets.",
                    data_point_id=data_point.data_point_id,
                )
            )
    return violations


def _match_key(point: ExpectedDataPoint) -> tuple[str, str, str]:
    return (
        _normalize(point.category),
        _normalize(point.field_name),
        _normalize(point.value),
    )


def _actual_key(data_point: DataPoint) -> tuple[str, str, str]:
    return (
        _normalize(data_point.category),
        _normalize(data_point.field_name),
        _normalize(data_point.value),
    )


def _normalize(value: str) -> str:
    return " ".join(value.split()).casefold()


def _exact_provenance_match(point: ExpectedDataPoint, data_point: DataPoint) -> bool:
    span = data_point.source_span
    return (
        span.start_char == point.start_char
        and span.end_char == point.end_char
        and span.start_byte == point.start_byte
        and span.end_byte == point.end_byte
        and span.text == point.source_text
    )


__all__ = [
    "EvaluationError",
    "evaluate_report",
    "evaluate_report_file",
    "load_evaluation_case",
    "load_extraction_report",
]
