from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from extractor.evals.models import EvaluationCase, ExpectedDataPoint
from extractor.evals.mutation import (
    MutationDeclaredChange,
    MutationFixture,
    MutationFixtureResult,
    MutationSuiteManifest,
    MutationSuiteResult,
    SourceSensitivityFailure,
    evaluate_mutation_manifest,
    load_mutation_manifest,
)
from extractor.evals.scoring import (
    EvaluationError,
    load_evaluation_case,
    load_extraction_report,
)


NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]
AdversarialMode = Literal[
    "paraphrase",
    "reordering",
    "distractor_insertion",
    "label_replacement",
    "formatting_change",
]


class RobustnessModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AdversarialFixturePair(RobustnessModel):
    pair_id: NonEmptyStr
    mode: AdversarialMode
    base_fixture_id: NonEmptyStr
    variant_fixture_id: NonEmptyStr
    base_case_path: NonEmptyStr
    base_report_path: NonEmptyStr
    variant_case_path: NonEmptyStr
    variant_report_path: NonEmptyStr

    @model_validator(mode="after")
    def validate_fixture_ids(self) -> AdversarialFixturePair:
        if self.base_fixture_id == self.variant_fixture_id:
            raise ValueError("adversarial pair must use distinct fixture IDs")
        return self


class AdversarialSuiteManifest(RobustnessModel):
    suite_id: NonEmptyStr
    description: NonEmptyStr
    pairs: tuple[AdversarialFixturePair, ...] = ()

    @model_validator(mode="after")
    def validate_pair_ids(self) -> AdversarialSuiteManifest:
        pair_ids = [pair.pair_id for pair in self.pairs]
        if len(pair_ids) != len(set(pair_ids)):
            raise ValueError("duplicate adversarial pair IDs")
        return self


def load_adversarial_manifest(
    manifest_path: str | Path,
    *,
    repo_root: str | Path | None = None,
) -> AdversarialSuiteManifest:
    path = Path(manifest_path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluationError(f"Failed to read adversarial manifest: {path}") from exc

    try:
        manifest = AdversarialSuiteManifest.model_validate(raw)
    except ValidationError as exc:
        raise EvaluationError(f"Invalid adversarial manifest: {path}: {exc}") from exc

    resolved_root = (Path(repo_root) if repo_root is not None else Path.cwd()).resolve()
    for pair in manifest.pairs:
        paths = _validate_repo_relative_files(
            pair_id=pair.pair_id,
            repo_root=resolved_root,
            values={
                "base_case_path": pair.base_case_path,
                "base_report_path": pair.base_report_path,
                "variant_case_path": pair.variant_case_path,
                "variant_report_path": pair.variant_report_path,
            },
        )
        base_case = load_evaluation_case(paths["base_case_path"])
        variant_case = load_evaluation_case(paths["variant_case_path"])
        load_extraction_report(paths["base_report_path"])
        load_extraction_report(paths["variant_report_path"])
        _validate_no_changed_text_copied_offsets(
            pair_id=pair.pair_id,
            base_case=base_case,
            variant_case=variant_case,
        )
    return manifest


def _validate_repo_relative_files(
    *,
    pair_id: str,
    repo_root: Path,
    values: dict[str, str],
) -> dict[str, Path]:
    return {
        label: _validate_repo_relative_file(
            pair_id=pair_id,
            path_value=value,
            path_label=label,
            repo_root=repo_root,
        )
        for label, value in values.items()
    }


def _validate_repo_relative_file(
    *,
    pair_id: str,
    path_value: str,
    path_label: str,
    repo_root: Path,
) -> Path:
    relative_path = Path(path_value)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise EvaluationError(
            f"Adversarial pair {pair_id} {path_label} must be repo-relative: {path_value}"
        )

    resolved_path = (repo_root / relative_path).resolve()
    try:
        resolved_path.relative_to(repo_root)
    except ValueError as exc:
        raise EvaluationError(
            f"Adversarial pair {pair_id} {path_label} must be repo-relative: {path_value}"
        ) from exc

    if not resolved_path.is_file():
        raise EvaluationError(
            f"Adversarial pair {pair_id} {path_label} does not exist: {path_value}"
        )
    return resolved_path


def _validate_no_changed_text_copied_offsets(
    *,
    pair_id: str,
    base_case: EvaluationCase,
    variant_case: EvaluationCase,
) -> None:
    base_points = {point.expected_id: point for point in base_case.expected_data_points}
    for variant_point in variant_case.expected_data_points:
        base_point = base_points.get(variant_point.expected_id)
        if base_point is None:
            continue
        if _same_offsets(base_point, variant_point) and (
            base_point.source_text != variant_point.source_text
        ):
            raise EvaluationError(
                "Adversarial pair "
                f"{pair_id} copied offsets with changed source text: "
                f"{variant_point.expected_id}"
            )


def _same_offsets(left: ExpectedDataPoint, right: ExpectedDataPoint) -> bool:
    return (
        left.start_char == right.start_char
        and left.end_char == right.end_char
        and left.start_byte == right.start_byte
        and left.end_byte == right.end_byte
    )


__all__ = [
    "AdversarialFixturePair",
    "AdversarialMode",
    "AdversarialSuiteManifest",
    "MutationDeclaredChange",
    "MutationFixture",
    "MutationFixtureResult",
    "MutationSuiteManifest",
    "MutationSuiteResult",
    "SourceSensitivityFailure",
    "evaluate_mutation_manifest",
    "load_adversarial_manifest",
    "load_mutation_manifest",
]
