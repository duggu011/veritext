from __future__ import annotations

import json
from pathlib import Path

from pydantic import Field, ValidationError, model_validator

from extractor.evals.models import (
    EvalModel,
    EvaluationThresholds,
    NonEmptyStr,
)
from extractor.evals.scoring import EvaluationError


class SuiteMetricThresholds(EvaluationThresholds):
    invariant_allowance_rationale: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_invariant_allowance(self) -> SuiteMetricThresholds:
        if (
            self.max_invariant_violations > 0
            and self.invariant_allowance_rationale is None
        ):
            raise ValueError("non-zero invariant allowance requires rationale")
        return self


class EvaluationSuiteFixture(EvalModel):
    fixture_id: NonEmptyStr
    case_path: NonEmptyStr
    report_path: NonEmptyStr


class CategoryThreshold(EvalModel):
    category: NonEmptyStr
    thresholds: SuiteMetricThresholds = Field(default_factory=SuiteMetricThresholds)


class FieldThreshold(EvalModel):
    category: NonEmptyStr
    field_name: NonEmptyStr
    thresholds: SuiteMetricThresholds = Field(default_factory=SuiteMetricThresholds)


class EvaluationSuiteThresholds(EvalModel):
    global_thresholds: SuiteMetricThresholds = Field(
        default_factory=SuiteMetricThresholds,
        alias="global",
    )
    categories: tuple[CategoryThreshold, ...] = ()
    fields: tuple[FieldThreshold, ...] = ()

    @model_validator(mode="after")
    def validate_threshold_keys(self) -> EvaluationSuiteThresholds:
        category_keys = [threshold.category for threshold in self.categories]
        if len(category_keys) != len(set(category_keys)):
            raise ValueError("duplicate category threshold keys")

        field_keys = [
            (threshold.category, threshold.field_name) for threshold in self.fields
        ]
        if len(field_keys) != len(set(field_keys)):
            raise ValueError("duplicate field threshold keys")
        return self


class EvaluationSuiteManifest(EvalModel):
    suite_id: NonEmptyStr
    description: NonEmptyStr
    fixtures: tuple[EvaluationSuiteFixture, ...] = Field(min_length=1)
    thresholds: EvaluationSuiteThresholds = Field(
        default_factory=EvaluationSuiteThresholds
    )

    @model_validator(mode="after")
    def validate_fixture_ids(self) -> EvaluationSuiteManifest:
        fixture_ids = [fixture.fixture_id for fixture in self.fixtures]
        if len(fixture_ids) != len(set(fixture_ids)):
            raise ValueError("duplicate suite fixture IDs")
        return self


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
    "load_suite_manifest",
]
