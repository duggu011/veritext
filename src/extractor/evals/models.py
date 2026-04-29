from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
Score = Annotated[float, Field(strict=True, ge=0.0, le=1.0)]
Sha256Hex = Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]


class EvalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExpectedDataPoint(EvalModel):
    expected_id: NonEmptyStr
    category: NonEmptyStr
    field_name: NonEmptyStr
    value: NonEmptyStr
    source_text: NonEmptyStr
    start_char: NonNegativeInt
    end_char: NonNegativeInt
    start_byte: NonNegativeInt
    end_byte: NonNegativeInt

    @model_validator(mode="after")
    def validate_offsets(self) -> ExpectedDataPoint:
        if self.end_char <= self.start_char:
            raise ValueError("expected end_char must be greater than start_char")
        if self.end_byte <= self.start_byte:
            raise ValueError("expected end_byte must be greater than start_byte")
        if len(self.source_text) != self.end_char - self.start_char:
            raise ValueError("expected source_text length must match character offsets")
        if len(self.source_text.encode("utf-8")) != self.end_byte - self.start_byte:
            raise ValueError("expected source_text byte length must match byte offsets")
        return self


class EvaluationThresholds(EvalModel):
    min_precision: Score = 1.0
    min_recall: Score = 1.0
    min_f1: Score = 1.0
    min_provenance_recall: Score = 1.0
    max_invariant_violations: NonNegativeInt = 0


class EvaluationCase(EvalModel):
    case_id: NonEmptyStr
    source_path: NonEmptyStr
    source_sha256: Sha256Hex
    source_text: NonEmptyStr
    expected_data_points: tuple[ExpectedDataPoint, ...] = Field(min_length=1)
    thresholds: EvaluationThresholds = Field(default_factory=EvaluationThresholds)

    @model_validator(mode="after")
    def validate_expected_points(self) -> EvaluationCase:
        expected_ids = [point.expected_id for point in self.expected_data_points]
        if len(expected_ids) != len(set(expected_ids)):
            raise ValueError("expected data point IDs must be unique")

        source_bytes = self.source_text.encode("utf-8")
        for point in self.expected_data_points:
            if point.end_char > len(self.source_text):
                raise ValueError(f"expected source span exceeds source text: {point.expected_id}")
            if point.end_byte > len(source_bytes):
                raise ValueError(f"expected source byte span exceeds source text: {point.expected_id}")
            if self.source_text[point.start_char : point.end_char] != point.source_text:
                raise ValueError(f"expected source span text mismatch: {point.expected_id}")
            if source_bytes[point.start_byte : point.end_byte] != point.source_text.encode("utf-8"):
                raise ValueError(f"expected source byte span mismatch: {point.expected_id}")
            if len(self.source_text[: point.start_char].encode("utf-8")) != point.start_byte:
                raise ValueError(f"expected start_byte is not aligned to start_char: {point.expected_id}")
            if len(self.source_text[: point.end_char].encode("utf-8")) != point.end_byte:
                raise ValueError(f"expected end_byte is not aligned to end_char: {point.expected_id}")
        return self


class DataPointMatch(EvalModel):
    expected_id: NonEmptyStr
    data_point_id: NonEmptyStr
    exact_provenance: bool = Field(strict=True)


class InvariantViolation(EvalModel):
    code: NonEmptyStr
    message: NonEmptyStr
    data_point_id: str | None = None


class EvaluationMetrics(EvalModel):
    expected_count: NonNegativeInt
    actual_count: NonNegativeInt
    true_positives: NonNegativeInt
    false_positives: NonNegativeInt
    false_negatives: NonNegativeInt
    precision: Score
    recall: Score
    f1: Score
    exact_provenance_matches: NonNegativeInt
    provenance_recall: Score
    invariant_violation_count: NonNegativeInt


class EvaluationResult(EvalModel):
    case_id: NonEmptyStr
    run_id: NonEmptyStr
    doc_id: NonEmptyStr
    metrics: EvaluationMetrics
    matches: tuple[DataPointMatch, ...]
    missing_expected_ids: tuple[NonEmptyStr, ...]
    unexpected_data_point_ids: tuple[NonEmptyStr, ...]
    invariant_violations: tuple[InvariantViolation, ...]
    passed: bool = Field(strict=True)


__all__ = [
    "DataPointMatch",
    "EvaluationCase",
    "EvaluationMetrics",
    "EvaluationResult",
    "EvaluationThresholds",
    "ExpectedDataPoint",
    "InvariantViolation",
]
