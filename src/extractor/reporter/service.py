from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from extractor.audit import AuditStore
from extractor.contracts import (
    ApprovedSchemaMetadata,
    CrossDocumentReconciliationResult,
    CrossDocumentRunManifest,
    DataPoint,
    PlanningRefusal,
    RunManifest,
)
from extractor.reporter.models import (
    CrossDocumentReport,
    ExtractionRefusalReport,
    ExtractionReport,
    ReportWriteResult,
)


class ReporterError(RuntimeError):
    """Raised when final output cannot be serialized without audit gaps."""


async def write_report(
    *,
    manifest: RunManifest,
    data_points: tuple[DataPoint, ...],
    schema_metadata: ApprovedSchemaMetadata,
    output_path: str | Path,
    audit_store: AuditStore | None = None,
    generated_at: datetime | None = None,
) -> ReportWriteResult:
    ordered_data_points = _ordered_data_points(data_points)
    _validate_report_inputs(manifest, ordered_data_points)

    if audit_store is not None:
        await _validate_audit_state(
            audit_store=audit_store,
            manifest=manifest,
            data_points=ordered_data_points,
        )

    completed_at = generated_at or datetime.now(timezone.utc)
    try:
        completed_manifest = RunManifest(
            run_id=manifest.run_id,
            doc_id=manifest.doc_id,
            audit_db_path=manifest.audit_db_path,
            status="completed",
            started_at=manifest.started_at,
            completed_at=completed_at,
            output_data_point_ids=tuple(
                data_point.data_point_id for data_point in ordered_data_points
            ),
        )
        report = ExtractionReport(
            report_schema_version="report.v2",
            run_id=manifest.run_id,
            doc_id=manifest.doc_id,
            generated_at=completed_at,
            schema_metadata=schema_metadata,
            output_data_point_ids=completed_manifest.output_data_point_ids,
            data_points=ordered_data_points,
        )
    except ValidationError as exc:
        raise ReporterError(f"Invalid final report state: {exc}") from exc

    rendered = render_report_json(report)
    output = Path(output_path)
    _write_output(output, rendered)

    if audit_store is not None:
        await audit_store.update_run_manifest(completed_manifest)

    output_bytes = rendered.encode("utf-8")
    return ReportWriteResult(
        report=report,
        output_path=str(output),
        output_sha256=hashlib.sha256(output_bytes).hexdigest(),
        output_byte_length=len(output_bytes),
        completed_manifest=completed_manifest,
    )


def render_report_json(report: ExtractionReport) -> str:
    return json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


async def write_refusal_report(
    *,
    manifest: RunManifest,
    refusal: PlanningRefusal,
    output_path: str | Path,
    audit_store: AuditStore | None = None,
    generated_at: datetime | None = None,
) -> ReportWriteResult:
    _validate_refusal_report_inputs(manifest, refusal)

    if audit_store is not None:
        stored_manifest = await audit_store.get_run_manifest(manifest.run_id)
        if stored_manifest is None:
            raise ReporterError(f"Run manifest is missing from audit store: {manifest.run_id}")
        if stored_manifest != manifest:
            raise ReporterError(
                "Run manifest must match the current audit store state before reporting"
            )

    completed_at = generated_at or datetime.now(timezone.utc)
    try:
        completed_manifest = RunManifest(
            run_id=manifest.run_id,
            doc_id=manifest.doc_id,
            audit_db_path=manifest.audit_db_path,
            status="refused",
            started_at=manifest.started_at,
            completed_at=completed_at,
            output_data_point_ids=(),
        )
        report = ExtractionRefusalReport(
            report_schema_version="refusal.v1",
            outcome_type="schema_fit_refusal",
            run_id=manifest.run_id,
            doc_id=manifest.doc_id,
            generated_at=completed_at,
            refusal=refusal,
        )
    except ValidationError as exc:
        raise ReporterError(f"Invalid refusal report state: {exc}") from exc

    rendered = render_report_json(report)
    output = Path(output_path)
    _write_output(output, rendered)

    if audit_store is not None:
        await audit_store.update_run_manifest(completed_manifest)

    output_bytes = rendered.encode("utf-8")
    return ReportWriteResult(
        report=report,
        output_path=str(output),
        output_sha256=hashlib.sha256(output_bytes).hexdigest(),
        output_byte_length=len(output_bytes),
        completed_manifest=completed_manifest,
    )


async def write_cross_document_report(
    *,
    manifest: CrossDocumentRunManifest,
    result: CrossDocumentReconciliationResult,
    output_path: str | Path,
    audit_store: AuditStore | None = None,
    generated_at: datetime | None = None,
) -> ReportWriteResult:
    _validate_cross_document_report_inputs(manifest, result)

    if audit_store is not None:
        await _validate_cross_document_audit_state(
            audit_store=audit_store,
            manifest=manifest,
            result=result,
        )

    completed_at = generated_at or datetime.now(timezone.utc)
    try:
        completed_manifest = CrossDocumentRunManifest(
            cross_document_run_id=manifest.cross_document_run_id,
            audit_db_path=manifest.audit_db_path,
            status="completed",
            started_at=manifest.started_at,
            completed_at=completed_at,
            input_run_ids=result.input_run_ids,
            output_group_ids=tuple(group.group_id for group in result.groups),
            output_conflict_ids=tuple(conflict.conflict_id for conflict in result.conflicts),
        )
        report = CrossDocumentReport.from_result(
            result=result,
            generated_at=completed_at,
        )
    except ValidationError as exc:
        raise ReporterError(f"Invalid cross-document report state: {exc}") from exc

    rendered = render_report_json(report)
    output = Path(output_path)
    _write_output(output, rendered)

    if audit_store is not None:
        await audit_store.update_cross_document_run_manifest(completed_manifest)

    output_bytes = rendered.encode("utf-8")
    return ReportWriteResult(
        report=report,
        output_path=str(output),
        output_sha256=hashlib.sha256(output_bytes).hexdigest(),
        output_byte_length=len(output_bytes),
        completed_manifest=completed_manifest,
    )


def _validate_refusal_report_inputs(
    manifest: RunManifest,
    refusal: PlanningRefusal,
) -> None:
    if manifest.status == "failed":
        raise ReporterError("failed runs cannot be refused by the reporter")
    if manifest.status == "completed":
        raise ReporterError("completed runs cannot be refused by the reporter")
    if refusal.run_id != manifest.run_id:
        raise ReporterError("refusal run_id must match run manifest run_id")
    if refusal.doc_id != manifest.doc_id:
        raise ReporterError("refusal doc_id must match run manifest doc_id")


async def _validate_audit_state(
    *,
    audit_store: AuditStore,
    manifest: RunManifest,
    data_points: tuple[DataPoint, ...],
) -> None:
    stored_manifest = await audit_store.get_run_manifest(manifest.run_id)
    if stored_manifest is None:
        raise ReporterError(f"Run manifest is missing from audit store: {manifest.run_id}")
    if stored_manifest != manifest:
        raise ReporterError("Run manifest must match the current audit store state before reporting")

    for data_point in data_points:
        stored_data_point = await audit_store.get_data_point(data_point.data_point_id)
        if stored_data_point is None:
            raise ReporterError(f"Data point is missing from audit store: {data_point.data_point_id}")
        if stored_data_point != data_point:
            raise ReporterError(
                f"Data point does not match the current audit store state: {data_point.data_point_id}"
            )


async def _validate_cross_document_audit_state(
    *,
    audit_store: AuditStore,
    manifest: CrossDocumentRunManifest,
    result: CrossDocumentReconciliationResult,
) -> None:
    stored_manifest = await audit_store.get_cross_document_run_manifest(
        manifest.cross_document_run_id
    )
    if stored_manifest is None:
        raise ReporterError(
            "Cross-document run manifest is missing from audit store: "
            f"{manifest.cross_document_run_id}"
        )
    if stored_manifest != manifest:
        raise ReporterError(
            "Cross-document run manifest must match the current audit store state before reporting"
        )

    stored_result = await audit_store.get_cross_document_reconciliation_result(
        result.cross_document_run_id
    )
    if stored_result is None:
        raise ReporterError(
            "Cross-document result is missing from audit store: "
            f"{result.cross_document_run_id}"
        )
    if stored_result != result:
        raise ReporterError(
            "Cross-document result must match the current audit store state before reporting"
        )


def _validate_cross_document_report_inputs(
    manifest: CrossDocumentRunManifest,
    result: CrossDocumentReconciliationResult,
) -> None:
    if manifest.status == "failed":
        raise ReporterError("failed cross-document runs cannot be completed by the reporter")
    if manifest.cross_document_run_id != result.cross_document_run_id:
        raise ReporterError("result run ID must match cross-document manifest run ID")


def _validate_report_inputs(
    manifest: RunManifest,
    data_points: tuple[DataPoint, ...],
) -> None:
    if manifest.status == "failed":
        raise ReporterError("failed runs cannot be completed by the reporter")
    data_point_ids: set[str] = set()
    for data_point in data_points:
        if data_point.run_id != manifest.run_id:
            raise ReporterError("data point run_id must match run manifest run_id")
        if data_point.doc_id != manifest.doc_id:
            raise ReporterError("data point doc_id must match run manifest doc_id")
        if data_point.data_point_id in data_point_ids:
            raise ReporterError("data point IDs must be unique before reporting")
        data_point_ids.add(data_point.data_point_id)


def _ordered_data_points(data_points: tuple[DataPoint, ...]) -> tuple[DataPoint, ...]:
    return tuple(
        sorted(
            data_points,
            key=lambda data_point: (
                data_point.category,
                data_point.field_name,
                data_point.source_span.start_char,
                data_point.source_span.end_char,
                data_point.data_point_id,
            ),
        )
    )


def _write_output(output_path: Path, rendered: str) -> None:
    if output_path.exists() and output_path.is_dir():
        raise ReporterError(f"Report output path is a directory: {output_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_bytes = rendered.encode("utf-8")
    temp_path = output_path.with_name(
        f".{output_path.name}.{hashlib.sha256(output_bytes).hexdigest()[:16]}.tmp"
    )
    temp_path.write_bytes(output_bytes)
    temp_path.replace(output_path)


__all__ = [
    "ReporterError",
    "render_report_json",
    "write_cross_document_report",
    "write_refusal_report",
    "write_report",
]
