from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from extractor.contracts import (
    ApprovedSchemaMetadata,
    CrossDocumentConflict,
    CrossDocumentFactGroup,
    CrossDocumentReconciliationResult,
    CrossDocumentRunManifest,
    CrossDocumentSkippedInput,
    DataPoint,
    PlanningRefusal,
    RunManifest,
)


NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
Sha256Hex = Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
Timestamp = Annotated[datetime, Field(strict=True)]


class ReporterModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExtractionReport(ReporterModel):
    report_schema_version: Literal["report.v2"]
    run_id: NonEmptyStr
    doc_id: NonEmptyStr
    generated_at: Timestamp
    schema_metadata: ApprovedSchemaMetadata
    output_data_point_ids: tuple[NonEmptyStr, ...]
    data_points: tuple[DataPoint, ...]

    @model_validator(mode="after")
    def validate_report_identity(self) -> ExtractionReport:
        data_point_ids = tuple(data_point.data_point_id for data_point in self.data_points)
        if data_point_ids != self.output_data_point_ids:
            raise ValueError("output_data_point_ids must match serialized data point order")
        if len(data_point_ids) != len(set(data_point_ids)):
            raise ValueError("report data point IDs must be unique")
        for data_point in self.data_points:
            if data_point.run_id != self.run_id:
                raise ValueError("data point run_id must match report run_id")
            if data_point.doc_id != self.doc_id:
                raise ValueError("data point doc_id must match report doc_id")
        return self


class ExtractionRefusalReport(ReporterModel):
    report_schema_version: Literal["refusal.v1"]
    outcome_type: Literal["schema_fit_refusal"]
    run_id: NonEmptyStr
    doc_id: NonEmptyStr
    generated_at: Timestamp
    refusal: PlanningRefusal

    @model_validator(mode="after")
    def validate_refusal_identity(self) -> ExtractionRefusalReport:
        if self.refusal.run_id != self.run_id:
            raise ValueError("refusal run_id must match report run_id")
        if self.refusal.doc_id != self.doc_id:
            raise ValueError("refusal doc_id must match report doc_id")
        return self


class CrossDocumentReport(ReporterModel):
    report_schema_version: Literal["cross_document_report.v1"]
    cross_document_run_id: NonEmptyStr
    generated_at: Timestamp
    input_run_ids: tuple[NonEmptyStr, ...]
    input_doc_ids: tuple[NonEmptyStr, ...]
    output_group_ids: tuple[NonEmptyStr, ...]
    output_conflict_ids: tuple[NonEmptyStr, ...]
    groups: tuple[CrossDocumentFactGroup, ...]
    conflicts: tuple[CrossDocumentConflict, ...]
    skipped_inputs: tuple[CrossDocumentSkippedInput, ...]

    @model_validator(mode="after")
    def validate_cross_document_report(self) -> CrossDocumentReport:
        group_ids = tuple(group.group_id for group in self.groups)
        conflict_ids = tuple(conflict.conflict_id for conflict in self.conflicts)
        if group_ids != self.output_group_ids:
            raise ValueError("output_group_ids must match serialized group order")
        if conflict_ids != self.output_conflict_ids:
            raise ValueError("output_conflict_ids must match serialized conflict order")
        return self

    @classmethod
    def from_result(
        cls,
        *,
        result: CrossDocumentReconciliationResult,
        generated_at: datetime,
    ) -> CrossDocumentReport:
        return cls(
            report_schema_version="cross_document_report.v1",
            cross_document_run_id=result.cross_document_run_id,
            generated_at=generated_at,
            input_run_ids=result.input_run_ids,
            input_doc_ids=result.input_doc_ids,
            output_group_ids=tuple(group.group_id for group in result.groups),
            output_conflict_ids=tuple(conflict.conflict_id for conflict in result.conflicts),
            groups=result.groups,
            conflicts=result.conflicts,
            skipped_inputs=result.skipped_inputs,
        )


class ReportWriteResult(ReporterModel):
    report: ExtractionReport | ExtractionRefusalReport | CrossDocumentReport
    output_path: NonEmptyStr
    output_sha256: Sha256Hex
    output_byte_length: NonNegativeInt
    completed_manifest: RunManifest | CrossDocumentRunManifest


__all__ = [
    "CrossDocumentReport",
    "ExtractionRefusalReport",
    "ExtractionReport",
    "ReportWriteResult",
]
