from __future__ import annotations

from extractor.contracts import SourceSpan
from extractor.evals.models import EvaluationCase, InvariantViolation
from extractor.reporter import ExtractionReport


def report_invariant_violations(
    case: EvaluationCase,
    report: ExtractionReport,
) -> list[InvariantViolation]:
    violations: list[InvariantViolation] = []
    source_bytes = case.source_text.encode("utf-8")
    for data_point in report.data_points:
        violations.extend(
            _span_invariant_violations(
                case=case,
                source_bytes=source_bytes,
                span=data_point.source_span,
                data_point_id=data_point.data_point_id,
                code_prefix="source_span",
                label="source_span",
            )
        )
        for span in data_point.supporting_source_spans:
            violations.extend(
                _span_invariant_violations(
                    case=case,
                    source_bytes=source_bytes,
                    span=span,
                    data_point_id=data_point.data_point_id,
                    code_prefix="supporting_source_span",
                    label="supporting source span",
                )
            )
    return violations


def _span_invariant_violations(
    *,
    case: EvaluationCase,
    source_bytes: bytes,
    span: SourceSpan,
    data_point_id: str,
    code_prefix: str,
    label: str,
) -> list[InvariantViolation]:
    if span.end_char > len(case.source_text) or span.end_byte > len(source_bytes):
        return [
            InvariantViolation(
                code=f"{code_prefix}_out_of_bounds",
                message=f"Data point {label} exceeds the evaluation source text.",
                data_point_id=data_point_id,
            )
        ]

    violations: list[InvariantViolation] = []
    expected_start_byte = len(case.source_text[: span.start_char].encode("utf-8"))
    expected_end_byte = len(case.source_text[: span.end_char].encode("utf-8"))
    if span.start_byte != expected_start_byte or span.end_byte != expected_end_byte:
        violations.append(
            InvariantViolation(
                code=f"{code_prefix}_byte_offset_mismatch",
                message=f"Data point {label} byte offsets are not aligned to characters.",
                data_point_id=data_point_id,
            )
        )

    if case.source_text[span.start_char : span.end_char] != span.text:
        violations.append(
            InvariantViolation(
                code=f"{code_prefix}_text_mismatch",
                message=f"Data point {label}.text does not match source text.",
                data_point_id=data_point_id,
            )
        )
    if source_bytes[span.start_byte : span.end_byte] != span.text.encode("utf-8"):
        violations.append(
            InvariantViolation(
                code=f"{code_prefix}_byte_mismatch",
                message=f"Data point {label}.text does not match source bytes.",
                data_point_id=data_point_id,
            )
        )
    return violations


__all__ = ["report_invariant_violations"]
