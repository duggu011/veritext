from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from extractor.contracts import ApprovedSchemaMetadata, DataPoint, RunManifest


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


class ReportWriteResult(ReporterModel):
    report: ExtractionReport
    output_path: NonEmptyStr
    output_sha256: Sha256Hex
    output_byte_length: NonNegativeInt
    completed_manifest: RunManifest


__all__ = ["ExtractionReport", "ReportWriteResult"]
