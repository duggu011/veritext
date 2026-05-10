from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from pydantic import ValidationError

from extractor.evals.models import (
    CategoryThreshold,
    CategoryMetricBreakdown,
    EvaluationMetrics,
    EvaluationSuiteFixture,
    EvaluationSuiteFixtureResult,
    EvaluationSuiteManifest,
    EvaluationSuiteResult,
    EvaluationSuiteThresholds,
    EvaluationThresholds,
    FieldThreshold,
    FieldMetricBreakdown,
    SuiteMetricThresholds,
    ThresholdFailure,
)
from extractor.evals.scoring import (
    EvaluationError,
    evaluate_report,
    load_evaluation_case,
    load_extraction_report,
)


def load_suite_manifest(
    manifest_path: str | Path,
    *,
    repo_root: str | Path | None = None,
) -> EvaluationSuiteManifest:
    path = Path(manifest_path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluationError(f"Failed to read evaluation suite manifest: {path}") from exc

    try:
        manifest = EvaluationSuiteManifest.model_validate(raw)
    except ValidationError as exc:
        raise EvaluationError(f"Invalid evaluation suite manifest: {path}: {exc}") from exc

    root = Path(repo_root) if repo_root is not None else Path.cwd()
    resolved_root = root.resolve()
    for fixture in manifest.fixtures:
        _validate_repo_relative_file(
            fixture_id=fixture.fixture_id,
            path_value=fixture.case_path,
            path_label="case_path",
            repo_root=resolved_root,
        )
        _validate_repo_relative_file(
            fixture_id=fixture.fixture_id,
            path_value=fixture.report_path,
            path_label="report_path",
            repo_root=resolved_root,
        )
    return manifest


def evaluate_suite_manifest(
    manifest_path: str | Path,
    *,
    repo_root: str | Path | None = None,
) -> EvaluationSuiteResult:
    manifest = load_suite_manifest(manifest_path, repo_root=repo_root)
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    resolved_root = root.resolve()

    fixture_results: list[EvaluationSuiteFixtureResult] = []
    threshold_failures: list[ThresholdFailure] = []
    for fixture in manifest.fixtures:
        case = load_evaluation_case(resolved_root / fixture.case_path)
        report = load_extraction_report(resolved_root / fixture.report_path)
        result = evaluate_report(case, report)
        fixture_results.append(
            EvaluationSuiteFixtureResult(
                fixture_id=fixture.fixture_id,
                case_path=fixture.case_path,
                report_path=fixture.report_path,
                result=result,
                passed=result.passed,
            )
        )
        threshold_failures.extend(
            _threshold_failures_for_metrics(
                suite_id=manifest.suite_id,
                scope="fixture",
                metrics=result.metrics,
                thresholds=case.thresholds,
                fixture_id=fixture.fixture_id,
            )
        )

    suite_metrics = _merge_metrics(
        fixture_result.result.metrics for fixture_result in fixture_results
    )
    category_metrics = _merge_category_metrics(fixture_results)
    field_metrics = _merge_field_metrics(fixture_results)

    threshold_failures.extend(
        _threshold_failures_for_metrics(
            suite_id=manifest.suite_id,
            scope="suite",
            metrics=suite_metrics,
            thresholds=manifest.thresholds.global_thresholds,
        )
    )
    category_metrics_by_key = {
        breakdown.category: breakdown.metrics for breakdown in category_metrics
    }
    for category_threshold in manifest.thresholds.categories:
        threshold_failures.extend(
            _threshold_failures_for_metrics(
                suite_id=manifest.suite_id,
                scope="category",
                metrics=category_metrics_by_key.get(
                    category_threshold.category,
                    _empty_metrics(),
                ),
                thresholds=category_threshold.thresholds,
                category=category_threshold.category,
            )
        )

    field_metrics_by_key = {
        (breakdown.category, breakdown.field_name): breakdown.metrics
        for breakdown in field_metrics
    }
    for field_threshold in manifest.thresholds.fields:
        threshold_failures.extend(
            _threshold_failures_for_metrics(
                suite_id=manifest.suite_id,
                scope="field",
                metrics=field_metrics_by_key.get(
                    (field_threshold.category, field_threshold.field_name),
                    _empty_metrics(),
                ),
                thresholds=field_threshold.thresholds,
                category=field_threshold.category,
                field_name=field_threshold.field_name,
            )
        )

    return EvaluationSuiteResult(
        suite_id=manifest.suite_id,
        metrics=suite_metrics,
        category_metrics=tuple(category_metrics),
        field_metrics=tuple(field_metrics),
        fixtures=tuple(fixture_results),
        threshold_failures=tuple(threshold_failures),
        passed=(
            all(result.passed for result in fixture_results)
            and not threshold_failures
        ),
    )


def _merge_category_metrics(
    fixture_results: list[EvaluationSuiteFixtureResult],
) -> tuple[CategoryMetricBreakdown, ...]:
    metrics_by_category: dict[str, list[EvaluationMetrics]] = {}
    for fixture_result in fixture_results:
        for breakdown in fixture_result.result.category_metrics:
            metrics_by_category.setdefault(breakdown.category, []).append(
                breakdown.metrics
            )

    return tuple(
        CategoryMetricBreakdown(
            category=category,
            metrics=_merge_metrics(metrics),
        )
        for category, metrics in sorted(metrics_by_category.items())
    )


def _merge_field_metrics(
    fixture_results: list[EvaluationSuiteFixtureResult],
) -> tuple[FieldMetricBreakdown, ...]:
    metrics_by_field: dict[tuple[str, str], list[EvaluationMetrics]] = {}
    for fixture_result in fixture_results:
        for breakdown in fixture_result.result.field_metrics:
            metrics_by_field.setdefault(
                (breakdown.category, breakdown.field_name),
                [],
            ).append(breakdown.metrics)

    return tuple(
        FieldMetricBreakdown(
            category=category,
            field_name=field_name,
            metrics=_merge_metrics(metrics),
        )
        for (category, field_name), metrics in sorted(metrics_by_field.items())
    )


def _merge_metrics(metrics: Iterable[EvaluationMetrics]) -> EvaluationMetrics:
    metric_list = tuple(metrics)
    return _metrics_from_counts(
        expected_count=sum(metric.expected_count for metric in metric_list),
        actual_count=sum(metric.actual_count for metric in metric_list),
        true_positives=sum(metric.true_positives for metric in metric_list),
        exact_provenance_matches=sum(
            metric.exact_provenance_matches for metric in metric_list
        ),
        invariant_violation_count=sum(
            metric.invariant_violation_count for metric in metric_list
        ),
    )


def _empty_metrics() -> EvaluationMetrics:
    return _metrics_from_counts(
        expected_count=0,
        actual_count=0,
        true_positives=0,
        exact_provenance_matches=0,
        invariant_violation_count=0,
    )


def _metrics_from_counts(
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


def _threshold_failures_for_metrics(
    *,
    suite_id: str,
    scope: str,
    metrics: EvaluationMetrics,
    thresholds: EvaluationThresholds | SuiteMetricThresholds,
    fixture_id: str | None = None,
    category: str | None = None,
    field_name: str | None = None,
) -> list[ThresholdFailure]:
    failures: list[ThresholdFailure] = []
    minimum_checks = (
        ("precision", metrics.precision, thresholds.min_precision),
        ("recall", metrics.recall, thresholds.min_recall),
        ("f1", metrics.f1, thresholds.min_f1),
        (
            "provenance_recall",
            metrics.provenance_recall,
            thresholds.min_provenance_recall,
        ),
    )
    for metric, actual, threshold in minimum_checks:
        if actual < threshold:
            failures.append(
                _threshold_failure(
                    suite_id=suite_id,
                    scope=scope,
                    metric=metric,
                    actual=actual,
                    threshold=threshold,
                    comparator="min",
                    fixture_id=fixture_id,
                    category=category,
                    field_name=field_name,
                )
            )

    if metrics.invariant_violation_count > thresholds.max_invariant_violations:
        failures.append(
            _threshold_failure(
                suite_id=suite_id,
                scope=scope,
                metric="invariant_violation_count",
                actual=float(metrics.invariant_violation_count),
                threshold=float(thresholds.max_invariant_violations),
                comparator="max",
                fixture_id=fixture_id,
                category=category,
                field_name=field_name,
            )
        )
    return failures


def _threshold_failure(
    *,
    suite_id: str,
    scope: str,
    metric: str,
    actual: float,
    threshold: float,
    comparator: str,
    fixture_id: str | None,
    category: str | None,
    field_name: str | None,
) -> ThresholdFailure:
    return ThresholdFailure(
        suite_id=suite_id,
        scope=scope,
        metric=metric,
        actual=float(actual),
        threshold=float(threshold),
        comparator=comparator,
        fixture_id=fixture_id,
        category=category,
        field_name=field_name,
    )


def _validate_repo_relative_file(
    *,
    fixture_id: str,
    path_value: str,
    path_label: str,
    repo_root: Path,
) -> None:
    relative_path = Path(path_value)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise EvaluationError(
            f"Suite fixture {fixture_id} {path_label} must be repo-relative: {path_value}"
        )

    resolved_path = (repo_root / relative_path).resolve()
    try:
        resolved_path.relative_to(repo_root)
    except ValueError as exc:
        raise EvaluationError(
            f"Suite fixture {fixture_id} {path_label} must be repo-relative: {path_value}"
        ) from exc

    if not resolved_path.is_file():
        raise EvaluationError(
            f"Suite fixture {fixture_id} {path_label} does not exist: {path_value}"
        )


__all__ = [
    "CategoryThreshold",
    "EvaluationSuiteFixture",
    "EvaluationSuiteManifest",
    "EvaluationSuiteThresholds",
    "FieldThreshold",
    "SuiteMetricThresholds",
    "evaluate_suite_manifest",
    "load_suite_manifest",
]
