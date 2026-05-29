from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from extractor.audit import AuditStore
from extractor.config import ExtractorConfig
from extractor.contracts import CrossDocumentRunManifest
from extractor.llm import LLMClient
from extractor.orchestrator.errors import OrchestratorError
from extractor.orchestrator.models import (
    CrossDocumentBatchResult,
    PipelineRefusalResult,
    PipelineRunResult,
)
from extractor.orchestrator.service import run_extraction_pipeline
from extractor.reconciler.cross_document import reconcile_cross_document_data_points
from extractor.reporter import write_cross_document_report


async def run_cross_document_reconciliation_batch(
    *,
    source_paths: tuple[str | Path, ...],
    output_path: str | Path,
    config: ExtractorConfig,
    llm_client: LLMClient | None = None,
    cross_document_run_id: str | None = None,
    run_ids: tuple[str, ...] = (),
    domain_hints: tuple[str, ...] = (),
) -> CrossDocumentBatchResult:
    sources = tuple(Path(source_path) for source_path in source_paths)
    actual_run_ids = _resolve_run_ids(sources=sources, run_ids=run_ids)
    actual_cross_document_run_id = (
        cross_document_run_id or f"xrun-{uuid.uuid4().hex}"
    )
    output = Path(output_path)

    input_results = await _run_single_document_inputs(
        sources=sources,
        output_path=output,
        config=config,
        llm_client=llm_client,
        run_ids=actual_run_ids,
        domain_hints=domain_hints,
    )
    _validate_distinct_documents(input_results)

    started_at = datetime.now(timezone.utc)
    running_manifest = CrossDocumentRunManifest(
        cross_document_run_id=actual_cross_document_run_id,
        audit_db_path=str(config.audit.database_path),
        status="running",
        started_at=started_at,
        input_run_ids=actual_run_ids,
        output_group_ids=(),
        output_conflict_ids=(),
    )

    async with AuditStore(config.audit.database_path) as audit_store:
        await audit_store.record_cross_document_run_manifest(running_manifest)
        try:
            reconciliation = reconcile_cross_document_data_points(
                cross_document_run_id=actual_cross_document_run_id,
                data_points=tuple(
                    data_point
                    for result in input_results
                    for data_point in result.reconciliation.data_points
                ),
                documents=tuple(result.document for result in input_results),
                schema_metadata_by_run_id={
                    result.run_id: result.plan.schema_metadata
                    for result in input_results
                },
                run_manifests=tuple(
                    result.completed_manifest for result in input_results
                ),
            )
            await audit_store.record_cross_document_reconciliation_result(
                reconciliation
            )
            report = await write_cross_document_report(
                manifest=running_manifest,
                result=reconciliation,
                output_path=output,
                audit_store=audit_store,
            )
        except Exception:
            await _mark_cross_document_failed(
                audit_store=audit_store,
                manifest=running_manifest,
            )
            raise

    completed_manifest = report.completed_manifest
    if not isinstance(completed_manifest, CrossDocumentRunManifest):
        raise OrchestratorError("cross-document reporter returned a non-cross-document manifest")
    return CrossDocumentBatchResult(
        cross_document_run_id=actual_cross_document_run_id,
        input_results=input_results,
        reconciliation=reconciliation,
        report=report,
        completed_manifest=completed_manifest,
    )


async def _run_single_document_inputs(
    *,
    sources: tuple[Path, ...],
    output_path: Path,
    config: ExtractorConfig,
    llm_client: LLMClient | None,
    run_ids: tuple[str, ...],
    domain_hints: tuple[str, ...],
) -> tuple[PipelineRunResult, ...]:
    results: list[PipelineRunResult] = []
    for index, source_path in enumerate(sources):
        result = await run_extraction_pipeline(
            source_path=source_path,
            output_path=_single_document_output_path(output_path, index),
            config=config,
            llm_client=llm_client,
            run_id=run_ids[index],
            domain_hints=domain_hints,
        )
        if isinstance(result, PipelineRefusalResult):
            raise OrchestratorError(
                "cross-document batch stopped because an input run refused: "
                f"{result.run_id}"
            )
        results.append(result)
    return tuple(results)


def _resolve_run_ids(
    *,
    sources: tuple[Path, ...],
    run_ids: tuple[str, ...],
) -> tuple[str, ...]:
    if len(sources) < 2:
        raise OrchestratorError(
            "cross-document batch requires at least two source documents"
        )
    if run_ids and len(run_ids) != len(sources):
        raise OrchestratorError("run_ids must match the number of source documents")
    actual_run_ids = run_ids or tuple(f"run-{uuid.uuid4().hex}" for _ in sources)
    if len(actual_run_ids) != len(set(actual_run_ids)):
        raise OrchestratorError("run_ids must be unique")
    return actual_run_ids


def _validate_distinct_documents(results: tuple[PipelineRunResult, ...]) -> None:
    doc_ids = tuple(result.document.doc_id for result in results)
    if len(doc_ids) != len(set(doc_ids)):
        raise OrchestratorError("cross-document batch requires unique document IDs")


def _single_document_output_path(output_path: Path, index: int) -> Path:
    suffix = output_path.suffix or ".json"
    return output_path.with_name(f"{output_path.stem}.input-{index + 1}{suffix}")


async def _mark_cross_document_failed(
    *,
    audit_store: AuditStore,
    manifest: CrossDocumentRunManifest,
) -> None:
    failed_manifest = CrossDocumentRunManifest(
        cross_document_run_id=manifest.cross_document_run_id,
        audit_db_path=manifest.audit_db_path,
        status="failed",
        started_at=manifest.started_at,
        completed_at=datetime.now(timezone.utc),
        input_run_ids=manifest.input_run_ids,
        output_group_ids=manifest.output_group_ids,
        output_conflict_ids=manifest.output_conflict_ids,
    )
    await audit_store.update_cross_document_run_manifest(failed_manifest)


__all__ = ["run_cross_document_reconciliation_batch"]
