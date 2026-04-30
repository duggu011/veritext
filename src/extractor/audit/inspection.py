from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from extractor.audit.store import AuditStore
from extractor.contracts import (
    CriticReport,
    DataPoint,
    LLMCallLog,
    LensCandidate,
    RunManifest,
    VerifierReport,
)


CRITIC_BATCH_LIMIT = 6
VERIFIER_BATCH_LIMIT = 5


class AuditInspectionError(RuntimeError):
    """Raised when an audit database cannot be inspected."""


async def inspect_audit_database(
    database_path: str | Path,
    *,
    run_id: str | None = None,
    include_details: bool = False,
) -> dict[str, Any]:
    path = Path(database_path)
    if str(database_path) != ":memory:" and not path.is_file():
        raise AuditInspectionError(f"Audit database does not exist: {path}")

    async with AuditStore(path) as store:
        manifests = await store.list_run_manifests()
        if not manifests:
            raise AuditInspectionError(f"Audit database contains no runs: {path}")

        manifest = _select_manifest(manifests, run_id)
        document = await store.get_document(manifest.doc_id)
        plan = await store.get_extraction_plan(manifest.run_id)
        chunks = await store.list_chunks(manifest.doc_id)
        llm_calls = await store.list_llm_call_logs(manifest.run_id)
        candidates = await store.list_lens_candidates(manifest.run_id)
        critic_reports = await store.list_critic_reports_for_run(manifest.run_id)
        verifier_reports = await store.list_verifier_reports_for_run(manifest.run_id)
        data_points = await store.list_data_points(manifest.run_id)
        rejections = await store.list_candidate_rejections_for_run(manifest.run_id)
        usage_summary = await store.summarize_run(manifest.run_id)
        schema_version = await store.get_schema_version()

    dedup_duplicate_count = sum(
        1
        for rejection in rejections
        if rejection.stage == "dedup"
        and any(reason.code == "duplicate_candidate" for reason in rejection.reasons)
    )
    inspection: dict[str, Any] = {
        "database": {
            "path": str(path),
            "schema_version": schema_version,
        },
        "available_runs": tuple(_manifest_summary(item) for item in manifests),
        "run": _manifest_summary(manifest),
        "document": (
            None
            if document is None
            else {
                "doc_id": document.doc_id,
                "source_path": document.source_path,
                "format": document.format,
                "source_sha256": document.source_sha256,
                "text_sha256": document.text_sha256,
                "source_byte_length": document.source_byte_length,
                "text_byte_length": document.text_byte_length,
                "pages": len(document.page_map),
            }
        ),
        "plan": (
            None
            if plan is None
            else {
                "categories": tuple(category.name for category in plan.approved_categories),
                "enabled_lenses": plan.enabled_lenses,
                "chunk_window_tokens": plan.chunk_policy.window_tokens,
                "chunk_overlap_tokens": plan.chunk_policy.overlap_tokens,
            }
        ),
        "counts": {
            "chunks": len(chunks),
            "llm_calls": len(llm_calls),
            "candidates": {
                "total": len(candidates),
                "dedup_duplicates": dedup_duplicate_count,
                "canonical_after_dedup": len(candidates) - dedup_duplicate_count,
            },
            "critic_reports": _accepted_counts(critic_reports),
            "verifier_reports": _accepted_counts(verifier_reports),
            "candidate_rejections": {
                "total": len(rejections),
                "by_stage": _counter_dict(rejection.stage for rejection in rejections),
                "by_reason": _counter_dict(
                    reason.code
                    for rejection in rejections
                    for reason in rejection.reasons
                ),
            },
            "data_points": len(data_points),
        },
        "usage_summary": usage_summary,
        "acceptance_checks": _acceptance_checks(usage_summary),
    }

    if include_details:
        inspection["details"] = {
            "llm_calls": tuple(_llm_call_detail(log) for log in llm_calls),
            "candidates": tuple(_candidate_detail(candidate) for candidate in candidates),
            "critic_reports": tuple(_critic_report_detail(report) for report in critic_reports),
            "verifier_reports": tuple(
                _verifier_report_detail(report) for report in verifier_reports
            ),
            "candidate_rejections": tuple(
                {
                    "rejection_id": rejection.rejection_id,
                    "candidate_id": rejection.candidate_id,
                    "stage": rejection.stage,
                    "reasons": tuple(
                        {"code": reason.code, "message": reason.message}
                        for reason in rejection.reasons
                    ),
                    "created_at": rejection.created_at.isoformat(),
                }
                for rejection in rejections
            ),
            "data_points": tuple(_data_point_detail(data_point) for data_point in data_points),
        }

    return inspection


def _select_manifest(
    manifests: tuple[RunManifest, ...],
    run_id: str | None,
) -> RunManifest:
    if run_id is None:
        return manifests[0]
    for manifest in manifests:
        if manifest.run_id == run_id:
            return manifest
    raise AuditInspectionError(f"Run not found in audit database: {run_id}")


def _manifest_summary(manifest: RunManifest) -> dict[str, Any]:
    return {
        "run_id": manifest.run_id,
        "doc_id": manifest.doc_id,
        "status": manifest.status,
        "started_at": manifest.started_at.isoformat(),
        "completed_at": (
            None if manifest.completed_at is None else manifest.completed_at.isoformat()
        ),
        "output_data_point_ids": manifest.output_data_point_ids,
    }


def _accepted_counts(
    reports: tuple[CriticReport, ...] | tuple[VerifierReport, ...],
) -> dict[str, int]:
    accepted = sum(1 for report in reports if report.accepted)
    return {
        "total": len(reports),
        "accepted": accepted,
        "rejected": len(reports) - accepted,
    }


def _counter_dict(values: Any) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _acceptance_checks(usage_summary: dict[str, dict[str, int]]) -> dict[str, Any]:
    critic_calls = usage_summary.get("critic", {}).get("calls", 0)
    verifier_calls = usage_summary.get("verifier", {}).get("calls", 0)
    critic_cache_read_tokens = usage_summary.get("critic", {}).get("cache_read_tokens", 0)
    verifier_cache_read_tokens = usage_summary.get("verifier", {}).get("cache_read_tokens", 0)
    return {
        "critic_batches_le_6": {
            "passed": critic_calls <= CRITIC_BATCH_LIMIT,
            "actual": critic_calls,
            "limit": CRITIC_BATCH_LIMIT,
        },
        "verifier_batches_le_5": {
            "passed": verifier_calls <= VERIFIER_BATCH_LIMIT,
            "actual": verifier_calls,
            "limit": VERIFIER_BATCH_LIMIT,
        },
        "critic_cache_read_tokens_nonzero": {
            "passed": critic_cache_read_tokens > 0,
            "actual": critic_cache_read_tokens,
        },
        "verifier_cache_read_tokens_nonzero": {
            "passed": verifier_cache_read_tokens > 0,
            "actual": verifier_cache_read_tokens,
        },
    }


def _llm_call_detail(log: LLMCallLog) -> dict[str, Any]:
    return {
        "call_id": log.call_id,
        "stage": log.stage,
        "attempt": log.attempt,
        "model": log.model,
        "prompt_sha256": log.prompt_sha256,
        "input_tokens": log.input_tokens,
        "output_tokens": log.output_tokens,
        "cache_read_tokens": log.cache_read_tokens,
        "cache_creation_tokens": log.cache_creation_tokens,
        "latency_ms": log.latency_ms,
        "stop_reason": log.stop_reason,
        "tool_name": log.tool_name,
        "created_at": log.created_at.isoformat(),
    }


def _candidate_detail(candidate: LensCandidate) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "chunk_id": candidate.chunk_id,
        "lens": candidate.lens,
        "category": candidate.category,
        "field_name": candidate.field_name,
        "value": candidate.value,
        "confidence": candidate.confidence,
        "source_start_char": candidate.source_span.start_char,
        "source_end_char": candidate.source_span.end_char,
        "source_text": candidate.source_span.text,
    }


def _critic_report_detail(report: CriticReport) -> dict[str, Any]:
    return {
        "report_id": report.report_id,
        "candidate_id": report.candidate_id,
        "accepted": report.accepted,
        "plausibility_score": report.plausibility_score,
        "issue_codes": tuple(issue.code for issue in report.issues),
        "has_correction": report.corrected_candidate is not None,
    }


def _verifier_report_detail(report: VerifierReport) -> dict[str, Any]:
    return {
        "report_id": report.report_id,
        "candidate_id": report.candidate_id,
        "accepted": report.accepted,
        "span_verified": report.span_verified,
        "category_verified": report.category_verified,
        "alignment_score": report.alignment_score,
        "rejection_reason_codes": tuple(reason.code for reason in report.rejection_reasons),
    }


def _data_point_detail(data_point: DataPoint) -> dict[str, Any]:
    return {
        "data_point_id": data_point.data_point_id,
        "category": data_point.category,
        "field_name": data_point.field_name,
        "value": data_point.value,
        "confidence": data_point.confidence,
        "source_start_char": data_point.source_span.start_char,
        "source_end_char": data_point.source_span.end_char,
        "source_text": data_point.source_span.text,
        "contributing_candidate_ids": data_point.contributing_candidate_ids,
        "critic_report_ids": data_point.critic_report_ids,
        "verifier_report_ids": data_point.verifier_report_ids,
    }


__all__ = ["AuditInspectionError", "inspect_audit_database"]
