from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from extractor.audit import UsageSummary
from extractor.contracts import (
    Chunk,
    CrossDocumentReconciliationResult,
    CrossDocumentRunManifest,
    Document,
    ExtractionPlan,
    PlanningRefusal,
    RunManifest,
)
from extractor.critic import CriticResult
from extractor.executor import ExecutionResult
from extractor.reconciler import ReconciliationResult
from extractor.reporter import ReportWriteResult
from extractor.verifier import VerificationResult


NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]


class OrchestratorModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PipelineRunResult(OrchestratorModel):
    run_id: NonEmptyStr
    document: Document
    chunks: tuple[Chunk, ...]
    plan: ExtractionPlan
    execution: ExecutionResult
    critic: CriticResult
    verification: VerificationResult
    reconciliation: ReconciliationResult
    report: ReportWriteResult
    completed_manifest: RunManifest
    usage_summary: UsageSummary


class PipelineRefusalResult(OrchestratorModel):
    run_id: NonEmptyStr
    document: Document
    chunks: tuple[Chunk, ...]
    refusal: PlanningRefusal
    report: ReportWriteResult
    completed_manifest: RunManifest
    usage_summary: UsageSummary


PipelineResult = PipelineRunResult | PipelineRefusalResult


class CrossDocumentBatchResult(OrchestratorModel):
    cross_document_run_id: NonEmptyStr
    input_results: tuple[PipelineRunResult, ...] = Field(min_length=2)
    reconciliation: CrossDocumentReconciliationResult
    report: ReportWriteResult
    completed_manifest: CrossDocumentRunManifest


__all__ = [
    "CrossDocumentBatchResult",
    "PipelineRefusalResult",
    "PipelineResult",
    "PipelineRunResult",
]
