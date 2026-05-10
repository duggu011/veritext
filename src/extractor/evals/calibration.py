from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from extractor.evals.scoring import (
    EvaluationError,
    evaluate_report,
    load_evaluation_case,
    load_extraction_report,
)
from extractor.evals.suites import load_suite_manifest


DEFAULT_CALIBRATION_BINS = (
    (0.0, 0.5, False),
    (0.5, 0.8, False),
    (0.8, 0.9, False),
    (0.9, 0.95, False),
    (0.95, 1.0, True),
)
NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
Score = Annotated[float, Field(strict=True, ge=0.0, le=1.0)]


class CalibrationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CalibrationBin(CalibrationModel):
    lower_bound: Score
    upper_bound: Score
    includes_upper_bound: bool = Field(strict=True)
    count: NonNegativeInt
    average_confidence: Score
    exact_match_accuracy: Score
    exact_provenance_accuracy: Score
    calibration_gap: Score
    provenance_calibration_gap: Score
    representative_fixture_ids: tuple[NonEmptyStr, ...] = ()


class CalibrationReport(CalibrationModel):
    suite_id: NonEmptyStr
    suite_path: NonEmptyStr
    total_data_points: NonNegativeInt
    matched_data_points: NonNegativeInt
    unmatched_data_points: NonNegativeInt
    bins: tuple[CalibrationBin, ...]
    empty_bin_indexes: tuple[NonNegativeInt, ...]
    expected_calibration_error: Score
    provenance_calibration_error: Score
    passed: bool = Field(strict=True)


@dataclass(frozen=True)
class _CalibrationObservation:
    fixture_id: str
    confidence: float
    exact_match: bool
    exact_provenance: bool


def generate_calibration_report(
    suite_path: str | Path,
    *,
    repo_root: str | Path | None = None,
    bins: tuple[tuple[float, float, bool], ...] = DEFAULT_CALIBRATION_BINS,
) -> CalibrationReport:
    manifest = load_suite_manifest(suite_path, repo_root=repo_root)
    resolved_root = (Path(repo_root) if repo_root is not None else Path.cwd()).resolve()
    observations: list[_CalibrationObservation] = []

    for fixture in manifest.fixtures:
        case = load_evaluation_case(resolved_root / fixture.case_path)
        report = load_extraction_report(resolved_root / fixture.report_path)
        result = evaluate_report(case, report)
        matches_by_data_point = {match.data_point_id: match for match in result.matches}
        for data_point in report.data_points:
            match = matches_by_data_point.get(data_point.data_point_id)
            observations.append(
                _CalibrationObservation(
                    fixture_id=fixture.fixture_id,
                    confidence=float(data_point.confidence),
                    exact_match=match is not None,
                    exact_provenance=bool(match and match.exact_provenance),
                )
            )

    calibration_bins = _build_bins(observations, bins)
    total = len(observations)
    matched = sum(1 for observation in observations if observation.exact_match)
    return CalibrationReport(
        suite_id=manifest.suite_id,
        suite_path=str(Path(suite_path)),
        total_data_points=total,
        matched_data_points=matched,
        unmatched_data_points=total - matched,
        bins=tuple(calibration_bins),
        empty_bin_indexes=tuple(
            index for index, bin_result in enumerate(calibration_bins) if bin_result.count == 0
        ),
        expected_calibration_error=_weighted_gap(
            total=total,
            bins=calibration_bins,
            gap_name="calibration_gap",
        ),
        provenance_calibration_error=_weighted_gap(
            total=total,
            bins=calibration_bins,
            gap_name="provenance_calibration_gap",
        ),
        passed=True,
    )


def _build_bins(
    observations: list[_CalibrationObservation],
    bins: tuple[tuple[float, float, bool], ...],
) -> list[CalibrationBin]:
    observations_by_bin: list[list[_CalibrationObservation]] = [
        [] for _ in bins
    ]
    for observation in observations:
        observations_by_bin[_bin_index(observation.confidence, bins)].append(observation)

    return [
        _build_bin_result(
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            includes_upper_bound=includes_upper_bound,
            observations=bin_observations,
        )
        for (lower_bound, upper_bound, includes_upper_bound), bin_observations in zip(
            bins,
            observations_by_bin,
            strict=True,
        )
    ]


def _build_bin_result(
    *,
    lower_bound: float,
    upper_bound: float,
    includes_upper_bound: bool,
    observations: list[_CalibrationObservation],
) -> CalibrationBin:
    count = len(observations)
    average_confidence = (
        sum(observation.confidence for observation in observations) / count
        if count
        else 0.0
    )
    exact_match_accuracy = (
        sum(1 for observation in observations if observation.exact_match) / count
        if count
        else 0.0
    )
    exact_provenance_accuracy = (
        sum(1 for observation in observations if observation.exact_provenance) / count
        if count
        else 0.0
    )
    return CalibrationBin(
        lower_bound=float(lower_bound),
        upper_bound=float(upper_bound),
        includes_upper_bound=includes_upper_bound,
        count=count,
        average_confidence=average_confidence,
        exact_match_accuracy=exact_match_accuracy,
        exact_provenance_accuracy=exact_provenance_accuracy,
        calibration_gap=abs(average_confidence - exact_match_accuracy),
        provenance_calibration_gap=abs(average_confidence - exact_provenance_accuracy),
        representative_fixture_ids=_representative_fixture_ids(observations),
    )


def _bin_index(
    confidence: float,
    bins: tuple[tuple[float, float, bool], ...],
) -> int:
    for index, (lower_bound, upper_bound, includes_upper_bound) in enumerate(bins):
        if confidence < lower_bound:
            continue
        if confidence < upper_bound or (
            includes_upper_bound and confidence <= upper_bound
        ):
            return index
    raise EvaluationError(f"Confidence value does not fit calibration bins: {confidence}")


def _representative_fixture_ids(
    observations: list[_CalibrationObservation],
) -> tuple[str, ...]:
    fixture_ids: dict[str, None] = {}
    for observation in observations:
        fixture_ids.setdefault(observation.fixture_id, None)
    return tuple(fixture_ids)


def _weighted_gap(
    *,
    total: int,
    bins: list[CalibrationBin],
    gap_name: str,
) -> float:
    if total == 0:
        return 0.0
    return sum((bin_result.count / total) * getattr(bin_result, gap_name) for bin_result in bins)


__all__ = [
    "DEFAULT_CALIBRATION_BINS",
    "CalibrationBin",
    "CalibrationReport",
    "generate_calibration_report",
]
