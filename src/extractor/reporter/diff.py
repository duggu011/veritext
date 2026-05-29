from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from extractor.contracts import (
    DataPoint,
    ReportArtifactRef,
    RunDiffEntry,
    RunDiffFactRef,
    RunDiffKind,
    RunDiffReport,
)
from extractor.reporter.models import ExtractionReport
from extractor.reporter.signing import canonical_json_bytes, canonical_json_sha256


DIFF_KIND_ORDER: tuple[RunDiffKind, ...] = (
    "changed_value",
    "changed_provenance",
    "changed_confidence",
    "removed",
    "added",
    "ambiguous_match",
    "unchanged",
)
SUMMARY_KINDS: tuple[RunDiffKind, ...] = (
    "added",
    "removed",
    "changed_value",
    "changed_provenance",
    "changed_confidence",
    "unchanged",
    "ambiguous_match",
)


class RunDiffWriteResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    report: RunDiffReport
    output_path: str
    output_sha256: str
    output_byte_length: int


def diff_reports(
    *,
    base_report: ExtractionReport,
    candidate_report: ExtractionReport,
    diff_run_id: str,
    generated_at,
) -> RunDiffReport:
    entries = tuple(
        sorted(
            _diff_data_points(base_report.data_points, candidate_report.data_points),
            key=_entry_sort_key,
        )
    )
    return RunDiffReport(
        report_schema_version="run_diff_report.v1",
        diff_run_id=diff_run_id,
        generated_at=generated_at,
        base_artifact=_report_artifact(base_report),
        candidate_artifact=_report_artifact(candidate_report),
        entries=entries,
        summary_counts=_summary_counts(entries),
        signed_manifest_refs=(),
    )


def write_run_diff_report(*, report: RunDiffReport, output_path: str | Path) -> RunDiffWriteResult:
    rendered = render_run_diff_report_json(report)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    output_bytes = rendered.encode("utf-8")
    return RunDiffWriteResult(
        report=report,
        output_path=str(output),
        output_sha256=hashlib.sha256(output_bytes).hexdigest(),
        output_byte_length=len(output_bytes),
    )


def render_run_diff_report_json(report: RunDiffReport) -> str:
    return json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _diff_data_points(
    base_points: tuple[DataPoint, ...],
    candidate_points: tuple[DataPoint, ...],
) -> list[RunDiffEntry]:
    base_by_key = _group_by_key(base_points)
    candidate_by_key = _group_by_key(candidate_points)
    entries: list[RunDiffEntry] = []
    for key in sorted(set(base_by_key) | set(candidate_by_key)):
        old_points = base_by_key.get(key, ())
        new_points = candidate_by_key.get(key, ())
        if not old_points:
            entries.extend(_entry("added", (), (point,), "new_fact") for point in new_points)
            continue
        if not new_points:
            entries.extend(
                _entry("removed", (point,), (), "missing_in_candidate") for point in old_points
            )
            continue
        if len(old_points) != 1 or len(new_points) != 1:
            entries.append(
                _entry("ambiguous_match", old_points, new_points, "multiple_candidate_matches")
            )
            continue

        old_point = old_points[0]
        new_point = new_points[0]
        if _point_value(old_point) != _point_value(new_point):
            entries.append(
                _entry("changed_value", (old_point,), (new_point,), "canonical_value_changed")
            )
        elif old_point.source_span != new_point.source_span:
            entries.append(
                _entry("changed_provenance", (old_point,), (new_point,), "source_span_changed")
            )
        elif old_point.confidence != new_point.confidence:
            entries.append(
                _entry("changed_confidence", (old_point,), (new_point,), "confidence_changed")
            )
        else:
            entries.append(_entry("unchanged", (old_point,), (new_point,), "same_fact"))
    return entries


def _entry(
    diff_kind: RunDiffKind,
    old_points: tuple[DataPoint, ...],
    new_points: tuple[DataPoint, ...],
    reason: str,
) -> RunDiffEntry:
    seed = canonical_json_sha256(
        {
            "diff_kind": diff_kind,
            "old": tuple(point.data_point_id for point in old_points),
            "new": tuple(point.data_point_id for point in new_points),
            "reason": reason,
        }
    )[:16]
    return RunDiffEntry(
        diff_entry_id=f"diff-{diff_kind}-{seed}",
        diff_kind=diff_kind,
        old_refs=tuple(_fact_ref("base", point) for point in old_points),
        new_refs=tuple(_fact_ref("candidate", point) for point in new_points),
        reason=reason,
    )


def _fact_ref(side: str, data_point: DataPoint) -> RunDiffFactRef:
    return RunDiffFactRef(
        report_side=side,
        run_id=data_point.run_id,
        doc_id=data_point.doc_id,
        data_point_id=data_point.data_point_id,
        category=data_point.category,
        field_name=data_point.field_name,
        value=data_point.value,
        value_canonical=data_point.value_canonical,
        source_span=data_point.source_span,
        confidence=data_point.confidence,
        conflict_status=data_point.conflict_status,
        conflict_group_id=data_point.conflict_group_id,
        conflict_reason=data_point.conflict_reason,
    )


def _group_by_key(data_points: tuple[DataPoint, ...]) -> dict[tuple[str, ...], tuple[DataPoint, ...]]:
    grouped: dict[tuple[str, ...], list[DataPoint]] = defaultdict(list)
    for data_point in data_points:
        grouped[_fact_key(data_point)].append(data_point)
    return {
        key: tuple(sorted(points, key=lambda point: (point.source_span.start_char, point.data_point_id)))
        for key, points in grouped.items()
    }


def _fact_key(data_point: DataPoint) -> tuple[str, ...]:
    return (
        data_point.category,
        data_point.field_name,
        data_point.value_kind,
        data_point.normalization_policy_id or "",
        data_point.normalization_policy_version or "",
    )


def _point_value(data_point: DataPoint) -> str:
    return data_point.value_canonical or data_point.value


def _report_artifact(report: ExtractionReport) -> ReportArtifactRef:
    payload_bytes = canonical_json_bytes(report)
    return ReportArtifactRef(
        artifact_path=f"{report.run_id}.json",
        report_schema_version=report.report_schema_version,
        artifact_sha256=hashlib.sha256(payload_bytes).hexdigest(),
        byte_length=len(payload_bytes),
        run_id=report.run_id,
        doc_id=report.doc_id,
    )


def _summary_counts(entries: tuple[RunDiffEntry, ...]) -> dict[RunDiffKind, int]:
    counts = Counter(entry.diff_kind for entry in entries)
    return {kind: counts.get(kind, 0) for kind in SUMMARY_KINDS}


def _entry_sort_key(entry: RunDiffEntry) -> tuple[int, str]:
    return (DIFF_KIND_ORDER.index(entry.diff_kind), entry.diff_entry_id)


__all__ = [
    "RunDiffWriteResult",
    "diff_reports",
    "render_run_diff_report_json",
    "write_run_diff_report",
]
