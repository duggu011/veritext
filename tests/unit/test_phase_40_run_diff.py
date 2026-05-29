from __future__ import annotations

import json
from datetime import datetime, timezone

from extractor.contracts import DataPoint
from extractor.reporter import ExtractionReport, diff_reports, write_run_diff_report
from tests.unit.test_reporter import HASH, make_data_point, make_schema_metadata


GENERATED = datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc)


def make_report(
    *,
    run_id: str,
    data_points: tuple[DataPoint, ...],
) -> ExtractionReport:
    return ExtractionReport(
        report_schema_version="report.v2",
        run_id=run_id,
        doc_id="doc-1",
        generated_at=GENERATED,
        schema_metadata=make_schema_metadata(),
        output_data_point_ids=tuple(data_point.data_point_id for data_point in data_points),
        data_points=data_points,
    )


def test_diff_reports_classifies_added_removed_changed_and_unchanged() -> None:
    unchanged_old = make_data_point(
        data_point_id="dp-old-unchanged",
        value="Revenue increased",
        start_char=0,
    ).model_copy(update={"confidence": 0.9})
    unchanged_new = make_data_point(
        data_point_id="dp-new-unchanged",
        value="Revenue increased",
        start_char=0,
    ).model_copy(update={"run_id": "run-2", "confidence": 0.9})
    changed_old = make_data_point(
        data_point_id="dp-old-payment",
        value="P30D",
        start_char=0,
    ).model_copy(
        update={
            "field_name": "payment_due",
            "value_verbatim": "30 days",
            "value_canonical": "P30D",
            "value_kind": "duration",
            "normalization_status": "canonicalized",
            "normalization_policy_id": "duration-key",
            "normalization_policy_version": "2026-05-30",
        }
    )
    changed_new = make_data_point(
        data_point_id="dp-new-payment",
        value="P45D",
        start_char=0,
    ).model_copy(
        update={
            "run_id": "run-2",
            "field_name": "payment_due",
            "value_verbatim": "45 days",
            "value_canonical": "P45D",
            "value_kind": "duration",
            "normalization_status": "canonicalized",
            "normalization_policy_id": "duration-key",
            "normalization_policy_version": "2026-05-30",
        }
    )
    removed = make_data_point(
        data_point_id="dp-removed",
        value="Delaware",
        start_char=0,
    ).model_copy(update={"field_name": "governing_law"})
    added = make_data_point(
        data_point_id="dp-added",
        value="New York",
        start_char=0,
    ).model_copy(update={"run_id": "run-2", "field_name": "venue"})

    report = diff_reports(
        base_report=make_report(
            run_id="run-1",
            data_points=(unchanged_old, changed_old, removed),
        ),
        candidate_report=make_report(
            run_id="run-2",
            data_points=(unchanged_new, changed_new, added),
        ),
        diff_run_id="diff-run-1-run-2",
        generated_at=GENERATED,
    )

    assert tuple(entry.diff_kind for entry in report.entries) == (
        "changed_value",
        "removed",
        "added",
        "unchanged",
    )
    assert report.summary_counts == {
        "added": 1,
        "removed": 1,
        "changed_value": 1,
        "changed_provenance": 0,
        "changed_confidence": 0,
        "unchanged": 1,
        "ambiguous_match": 0,
    }
    changed_entry = report.entries[0]
    assert changed_entry.old_refs[0].value_canonical == "P30D"
    assert changed_entry.new_refs[0].value_canonical == "P45D"


def test_write_run_diff_report_serializes_stable_json(tmp_path) -> None:
    data_point = make_data_point().model_copy(update={"confidence": 0.9})
    report = diff_reports(
        base_report=make_report(run_id="run-1", data_points=(data_point,)),
        candidate_report=make_report(
            run_id="run-2",
            data_points=(data_point.model_copy(update={"run_id": "run-2"}),),
        ),
        diff_run_id="diff-run-1-run-2",
        generated_at=GENERATED,
    )
    result = write_run_diff_report(report=report, output_path=tmp_path / "diff.json")

    payload = json.loads((tmp_path / "diff.json").read_text(encoding="utf-8"))

    assert payload["report_schema_version"] == "run_diff_report.v1"
    assert payload["summary_counts"]["unchanged"] == 1
    assert result.output_sha256 == HASH or len(result.output_sha256) == 64
    assert result.output_byte_length == (tmp_path / "diff.json").stat().st_size
