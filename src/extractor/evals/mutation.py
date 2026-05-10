from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from extractor.evals.models import EvaluationCase, EvaluationResult, ExpectedDataPoint
from extractor.evals.scoring import (
    EvaluationError,
    evaluate_report,
    load_evaluation_case,
    load_extraction_report,
)


NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]
Score = Annotated[float, Field(strict=True, ge=0.0, le=1.0)]


class MutationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MutationDeclaredChange(MutationModel):
    expected_id: NonEmptyStr
    retired_source_value: NonEmptyStr | None = None
    introduced_source_value: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_declared_values(self) -> MutationDeclaredChange:
        if self.retired_source_value is None and self.introduced_source_value is None:
            raise ValueError(
                "mutation change requires retired_source_value or introduced_source_value"
            )
        return self


class MutationFixture(MutationModel):
    mutation_id: NonEmptyStr
    base_fixture_id: NonEmptyStr
    mutated_fixture_id: NonEmptyStr
    base_case_path: NonEmptyStr
    base_report_path: NonEmptyStr
    mutated_case_path: NonEmptyStr
    mutated_report_path: NonEmptyStr
    changes: tuple[MutationDeclaredChange, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_fixture_ids(self) -> MutationFixture:
        if self.base_fixture_id == self.mutated_fixture_id:
            raise ValueError("mutation must use distinct fixture IDs")
        return self


class MutationSuiteManifest(MutationModel):
    suite_id: NonEmptyStr
    description: NonEmptyStr
    mutations: tuple[MutationFixture, ...] = ()

    @model_validator(mode="after")
    def validate_mutation_ids(self) -> MutationSuiteManifest:
        mutation_ids = [mutation.mutation_id for mutation in self.mutations]
        if len(mutation_ids) != len(set(mutation_ids)):
            raise ValueError("duplicate mutation IDs")
        return self


class SourceSensitivityFailure(MutationModel):
    mutation_id: NonEmptyStr
    expected_id: NonEmptyStr
    code: NonEmptyStr
    message: NonEmptyStr
    value: NonEmptyStr | None = None


class MutationFixtureResult(MutationModel):
    mutation_id: NonEmptyStr
    base_fixture_id: NonEmptyStr
    mutated_fixture_id: NonEmptyStr
    result: EvaluationResult
    source_sensitivity: Score
    source_sensitivity_failures: tuple[SourceSensitivityFailure, ...]
    passed: bool = Field(strict=True)


class MutationSuiteResult(MutationModel):
    suite_id: NonEmptyStr
    mutations: tuple[MutationFixtureResult, ...]
    source_sensitivity: Score
    passed: bool = Field(strict=True)


def load_mutation_manifest(
    manifest_path: str | Path,
    *,
    repo_root: str | Path | None = None,
) -> MutationSuiteManifest:
    path = Path(manifest_path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluationError(f"Failed to read mutation manifest: {path}") from exc

    try:
        manifest = MutationSuiteManifest.model_validate(raw)
    except ValidationError as exc:
        raise EvaluationError(f"Invalid mutation manifest: {path}: {exc}") from exc

    resolved_root = (Path(repo_root) if repo_root is not None else Path.cwd()).resolve()
    for mutation in manifest.mutations:
        paths = _validate_repo_relative_files(
            item_id=mutation.mutation_id,
            repo_root=resolved_root,
            values={
                "base_case_path": mutation.base_case_path,
                "base_report_path": mutation.base_report_path,
                "mutated_case_path": mutation.mutated_case_path,
                "mutated_report_path": mutation.mutated_report_path,
            },
        )
        base_case = load_evaluation_case(paths["base_case_path"])
        mutated_case = load_evaluation_case(paths["mutated_case_path"])
        load_extraction_report(paths["base_report_path"])
        load_extraction_report(paths["mutated_report_path"])
        _validate_mutation_changes(
            mutation_id=mutation.mutation_id,
            changes=mutation.changes,
            base_case=base_case,
            mutated_case=mutated_case,
        )
    return manifest


def evaluate_mutation_manifest(
    manifest_path: str | Path,
    *,
    repo_root: str | Path | None = None,
) -> MutationSuiteResult:
    manifest = load_mutation_manifest(manifest_path, repo_root=repo_root)
    resolved_root = (Path(repo_root) if repo_root is not None else Path.cwd()).resolve()
    mutation_results: list[MutationFixtureResult] = []
    for mutation in manifest.mutations:
        mutated_case = load_evaluation_case(resolved_root / mutation.mutated_case_path)
        mutated_report = load_extraction_report(
            resolved_root / mutation.mutated_report_path
        )
        result = evaluate_report(mutated_case, mutated_report)
        failures = _source_sensitivity_failures(
            mutation_id=mutation.mutation_id,
            changes=mutation.changes,
            actual_values=_actual_report_values(mutated_report.data_points),
        )
        source_sensitivity = _source_sensitivity_score(
            change_count=len(mutation.changes),
            failure_count=len({failure.expected_id for failure in failures}),
        )
        mutation_results.append(
            MutationFixtureResult(
                mutation_id=mutation.mutation_id,
                base_fixture_id=mutation.base_fixture_id,
                mutated_fixture_id=mutation.mutated_fixture_id,
                result=result,
                source_sensitivity=source_sensitivity,
                source_sensitivity_failures=tuple(failures),
                passed=result.passed and source_sensitivity == 1.0 and not failures,
            )
        )

    return MutationSuiteResult(
        suite_id=manifest.suite_id,
        mutations=tuple(mutation_results),
        source_sensitivity=_aggregate_source_sensitivity(mutation_results),
        passed=all(result.passed for result in mutation_results),
    )


def _validate_repo_relative_files(
    *,
    item_id: str,
    repo_root: Path,
    values: dict[str, str],
) -> dict[str, Path]:
    return {
        label: _validate_repo_relative_file(
            item_id=item_id,
            path_value=value,
            path_label=label,
            repo_root=repo_root,
        )
        for label, value in values.items()
    }


def _validate_repo_relative_file(
    *,
    item_id: str,
    path_value: str,
    path_label: str,
    repo_root: Path,
) -> Path:
    relative_path = Path(path_value)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise EvaluationError(
            f"Mutation {item_id} {path_label} must be repo-relative: {path_value}"
        )

    resolved_path = (repo_root / relative_path).resolve()
    try:
        resolved_path.relative_to(repo_root)
    except ValueError as exc:
        raise EvaluationError(
            f"Mutation {item_id} {path_label} must be repo-relative: {path_value}"
        ) from exc

    if not resolved_path.is_file():
        raise EvaluationError(
            f"Mutation {item_id} {path_label} does not exist: {path_value}"
        )
    return resolved_path


def _validate_mutation_changes(
    *,
    mutation_id: str,
    changes: tuple[MutationDeclaredChange, ...],
    base_case: EvaluationCase,
    mutated_case: EvaluationCase,
) -> None:
    base_points = {point.expected_id: point for point in base_case.expected_data_points}
    mutated_points = {
        point.expected_id: point for point in mutated_case.expected_data_points
    }
    for change in changes:
        if change.expected_id not in base_points and change.expected_id not in mutated_points:
            raise EvaluationError(
                f"Mutation {mutation_id} changed expected_id absent from fixtures: "
                f"{change.expected_id}"
            )
        if change.retired_source_value is not None:
            base_point = base_points.get(change.expected_id)
            if base_point is None or not _point_contains_value(
                base_point,
                change.retired_source_value,
            ):
                raise EvaluationError(
                    f"Mutation {mutation_id} retired_source_value absent from base "
                    f"fixture: {change.expected_id}"
                )
        if change.introduced_source_value is not None and not any(
            _point_contains_value(point, change.introduced_source_value)
            for point in mutated_case.expected_data_points
        ):
            raise EvaluationError(
                f"Mutation {mutation_id} introduced_source_value absent from mutated "
                f"fixture: {change.expected_id}"
            )


def _point_contains_value(point: ExpectedDataPoint, value: str) -> bool:
    normalized_value = _normalize_text(value)
    return any(
        normalized_value in _normalize_text(candidate)
        for candidate in (point.source_text, point.value)
    )


def _source_sensitivity_failures(
    *,
    mutation_id: str,
    changes: tuple[MutationDeclaredChange, ...],
    actual_values: tuple[str, ...],
) -> list[SourceSensitivityFailure]:
    failures: list[SourceSensitivityFailure] = []
    for change in changes:
        if change.retired_source_value is not None and _contains_value(
            actual_values,
            change.retired_source_value,
        ):
            failures.append(
                SourceSensitivityFailure(
                    mutation_id=mutation_id,
                    expected_id=change.expected_id,
                    code="retired_value_retained",
                    message="Mutation report retained a retired source value.",
                    value=change.retired_source_value,
                )
            )
        if change.introduced_source_value is not None and not _contains_value(
            actual_values,
            change.introduced_source_value,
        ):
            failures.append(
                SourceSensitivityFailure(
                    mutation_id=mutation_id,
                    expected_id=change.expected_id,
                    code="introduced_value_missing",
                    message="Mutation report omitted an introduced source value.",
                    value=change.introduced_source_value,
                )
            )
    return failures


def _actual_report_values(data_points: object) -> tuple[str, ...]:
    values: list[str] = []
    for data_point in data_points:
        values.append(data_point.value)
        values.append(data_point.source_span.text)
    return tuple(values)


def _contains_value(actual_values: tuple[str, ...], expected_value: str) -> bool:
    needle = _normalize_text(expected_value)
    return any(needle in _normalize_text(value) for value in actual_values)


def _source_sensitivity_score(*, change_count: int, failure_count: int) -> float:
    return 1.0 if change_count == 0 else (change_count - failure_count) / change_count


def _aggregate_source_sensitivity(
    mutation_results: list[MutationFixtureResult],
) -> float:
    if not mutation_results:
        return 1.0
    return sum(result.source_sensitivity for result in mutation_results) / len(
        mutation_results
    )


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).casefold()


__all__ = [
    "MutationDeclaredChange",
    "MutationFixture",
    "MutationFixtureResult",
    "MutationSuiteManifest",
    "MutationSuiteResult",
    "SourceSensitivityFailure",
    "evaluate_mutation_manifest",
    "load_mutation_manifest",
]
