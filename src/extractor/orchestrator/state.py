from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from extractor.audit import (
    AuditStore,
    CandidateRejection,
    RunStageName,
    RunStageState,
)
from extractor.config import ChunkingConfig
from extractor.contracts import (
    Chunk,
    CriticReport,
    DataPoint,
    Document,
    ExtractionPlan,
    LensCandidate,
    RunManifest,
    VerifierReport,
)
from extractor.critic import CriticResult
from extractor.executor import ExecutionResult
from extractor.ingestion import ingest_document
from extractor.orchestrator.errors import OrchestratorError
from extractor.reconciler import ReconciliationResult
from extractor.verifier import VerificationResult


async def load_resume_document(
    *,
    source_path: str | Path,
    manifest: RunManifest,
    audit_store: AuditStore,
) -> Document:
    document = await ingest_document(source_path, audit_store=None)
    if document.doc_id != manifest.doc_id:
        raise OrchestratorError(
            "Cannot resume: source document does not match the existing run "
            f"manifest doc_id {manifest.doc_id}."
        )

    stored_document = await audit_store.get_document(manifest.doc_id)
    if stored_document is None:
        await audit_store.record_document(document)
        return document
    if stored_document != document:
        raise OrchestratorError(
            "Cannot resume: source document payload differs from the audited "
            f"document {manifest.doc_id}."
        )
    return stored_document


def validate_resume_chunks(
    *,
    document: Document,
    chunks: tuple[Chunk, ...],
) -> tuple[Chunk, ...]:
    if not chunks:
        raise OrchestratorError("Cannot resume: audited chunk list is empty.")
    expected_indexes = tuple(range(len(chunks)))
    actual_indexes = tuple(chunk.chunk_index for chunk in chunks)
    if actual_indexes != expected_indexes:
        raise OrchestratorError("Cannot resume: audited chunk indexes are not contiguous.")
    for chunk in chunks:
        if chunk.doc_id != document.doc_id:
            raise OrchestratorError("Cannot resume: chunk doc_id does not match document.")
        if document.text[chunk.start_char : chunk.end_char] != chunk.text:
            raise OrchestratorError("Cannot resume: chunk text no longer matches document offsets.")
    return chunks


def validate_resume_plan(
    *,
    plan: ExtractionPlan,
    document: Document,
    chunking_config: ChunkingConfig,
) -> ExtractionPlan:
    if plan.doc_id != document.doc_id:
        raise OrchestratorError("Cannot resume: extraction plan doc_id does not match document.")
    if plan.chunk_policy.window_tokens != chunking_config.window_tokens:
        raise OrchestratorError("Cannot resume: configured chunk window changed since planning.")
    if plan.chunk_policy.overlap_tokens != chunking_config.overlap_tokens:
        raise OrchestratorError("Cannot resume: configured chunk overlap changed since planning.")
    return plan


async def ensure_stage_completed(
    audit_store: AuditStore,
    *,
    run_id: str,
    stage: RunStageName,
) -> None:
    if await audit_store.get_run_stage_state(run_id, stage) is not None:
        return
    await audit_store.record_run_stage_state(
        RunStageState(
            run_id=run_id,
            stage=stage,
            completed_at=datetime.now(timezone.utc),
        )
    )


def execution_result_from_audit(
    *,
    plan: ExtractionPlan,
    candidates: tuple[LensCandidate, ...],
    rejections: tuple[CandidateRejection, ...],
) -> ExecutionResult:
    for candidate in candidates:
        if candidate.run_id != plan.run_id:
            raise OrchestratorError("Cannot resume: candidate run_id does not match plan.")
        if candidate.doc_id != plan.doc_id:
            raise OrchestratorError("Cannot resume: candidate doc_id does not match plan.")

    executor_rejections = tuple(
        rejection for rejection in rejections if rejection.stage == "executor"
    )
    rejected_candidate_ids = {rejection.candidate_id for rejection in executor_rejections}
    candidates_by_id = _candidate_map(candidates)
    rejected_candidates = tuple(
        candidates_by_id[candidate_id]
        for candidate_id in sorted(rejected_candidate_ids)
        if candidate_id in candidates_by_id
    )
    accepted_candidates = tuple(
        candidate
        for candidate in candidates
        if candidate.candidate_id not in rejected_candidate_ids
    )
    return ExecutionResult(
        accepted_candidates=accepted_candidates,
        rejected_candidates=rejected_candidates,
        rejections=executor_rejections,
    )


def critic_complete(
    *,
    candidates: tuple[LensCandidate, ...],
    reports: tuple[CriticReport, ...],
    rejections: tuple[CandidateRejection, ...],
) -> bool:
    return _review_stage_complete(
        stage="critic",
        candidate_ids=tuple(candidate.candidate_id for candidate in candidates),
        report_candidate_ids=tuple(report.candidate_id for report in reports),
        rejections=rejections,
    )


def critic_result_from_audit(
    *,
    candidates: tuple[LensCandidate, ...],
    reports: tuple[CriticReport, ...],
    rejections: tuple[CandidateRejection, ...],
) -> CriticResult:
    candidates_by_id = _candidate_map(candidates)
    critic_rejections = tuple(
        rejection for rejection in rejections if rejection.stage == "critic"
    )
    accepted: list[LensCandidate] = []
    rejected_by_id: dict[str, LensCandidate] = {}
    reported_ids: set[str] = set()
    for report in reports:
        candidate = candidates_by_id.get(report.candidate_id)
        if candidate is None:
            raise OrchestratorError(
                f"Cannot resume: critic report references missing candidate {report.candidate_id}."
            )
        reported_ids.add(report.candidate_id)
        if report.accepted:
            accepted.append(report.corrected_candidate or candidate)
        else:
            rejected_by_id[report.candidate_id] = candidate

    for rejection in critic_rejections:
        candidate = candidates_by_id.get(rejection.candidate_id)
        if candidate is None:
            raise OrchestratorError(
                "Cannot resume: critic rejection references missing candidate "
                f"{rejection.candidate_id}."
            )
        if rejection.candidate_id not in reported_ids:
            rejected_by_id[rejection.candidate_id] = candidate

    return CriticResult(
        accepted_candidates=tuple(accepted),
        rejected_candidates=tuple(
            rejected_by_id[candidate_id] for candidate_id in sorted(rejected_by_id)
        ),
        reports=reports,
        rejections=critic_rejections,
    )


def verifier_complete(
    *,
    candidates: tuple[LensCandidate, ...],
    reports: tuple[VerifierReport, ...],
    rejections: tuple[CandidateRejection, ...],
) -> bool:
    return _review_stage_complete(
        stage="verifier",
        candidate_ids=tuple(candidate.candidate_id for candidate in candidates),
        report_candidate_ids=tuple(report.candidate_id for report in reports),
        rejections=rejections,
    )


def verification_result_from_audit(
    *,
    candidates: tuple[LensCandidate, ...],
    reports: tuple[VerifierReport, ...],
    rejections: tuple[CandidateRejection, ...],
) -> VerificationResult:
    candidates_by_id = _candidate_map(candidates)
    verifier_rejections = tuple(
        rejection for rejection in rejections if rejection.stage == "verifier"
    )
    accepted: list[LensCandidate] = []
    rejected_by_id: dict[str, LensCandidate] = {}
    reported_ids: set[str] = set()
    for report in reports:
        candidate = candidates_by_id.get(report.candidate_id)
        if candidate is None:
            raise OrchestratorError(
                "Cannot resume: verifier report references missing candidate "
                f"{report.candidate_id}."
            )
        reported_ids.add(report.candidate_id)
        if report.accepted:
            accepted.append(candidate)
        else:
            rejected_by_id[report.candidate_id] = candidate

    for rejection in verifier_rejections:
        candidate = candidates_by_id.get(rejection.candidate_id)
        if candidate is None:
            raise OrchestratorError(
                "Cannot resume: verifier rejection references missing candidate "
                f"{rejection.candidate_id}."
            )
        if rejection.candidate_id not in reported_ids:
            rejected_by_id[rejection.candidate_id] = candidate

    return VerificationResult(
        accepted_candidates=tuple(accepted),
        rejected_candidates=tuple(
            rejected_by_id[candidate_id] for candidate_id in sorted(rejected_by_id)
        ),
        reports=reports,
        rejections=verifier_rejections,
    )


def reconciler_complete(
    *,
    candidates: tuple[LensCandidate, ...],
    data_points: tuple[DataPoint, ...],
    rejections: tuple[CandidateRejection, ...],
) -> bool:
    if not candidates:
        return True
    expected = {candidate.candidate_id for candidate in candidates}
    reconciler_rejections = tuple(
        rejection for rejection in rejections if rejection.stage == "reconciler"
    )
    if not data_points and not reconciler_rejections:
        return False

    accounted: set[str] = set()
    for data_point in data_points:
        accounted.update(data_point.contributing_candidate_ids)
    accounted.update(rejection.candidate_id for rejection in reconciler_rejections)
    missing = expected - accounted
    if missing:
        raise OrchestratorError(
            "Cannot safely resume: audited reconciler output is partial for "
            f"candidates: {', '.join(sorted(missing))}."
        )
    return True


def reconciliation_result_from_audit(
    *,
    data_points: tuple[DataPoint, ...],
    rejections: tuple[CandidateRejection, ...],
) -> ReconciliationResult:
    return ReconciliationResult(
        data_points=data_points,
        rejections=tuple(
            rejection for rejection in rejections if rejection.stage == "reconciler"
        ),
    )


def transition_manifest(
    manifest: RunManifest,
    *,
    status: str,
    completed_at: datetime | None = None,
) -> RunManifest:
    return RunManifest(
        run_id=manifest.run_id,
        doc_id=manifest.doc_id,
        audit_db_path=manifest.audit_db_path,
        status=status,
        started_at=manifest.started_at,
        completed_at=completed_at,
        output_data_point_ids=manifest.output_data_point_ids,
    )


def _review_stage_complete(
    *,
    stage: str,
    candidate_ids: tuple[str, ...],
    report_candidate_ids: tuple[str, ...],
    rejections: tuple[CandidateRejection, ...],
) -> bool:
    if not candidate_ids:
        return True
    expected = set(candidate_ids)
    accounted = set(report_candidate_ids)
    accounted.update(
        rejection.candidate_id for rejection in rejections if rejection.stage == stage
    )
    relevant_accounted = expected & accounted
    if not relevant_accounted:
        return False
    missing = expected - accounted
    if missing:
        raise OrchestratorError(
            "Cannot safely resume: audited "
            f"{stage} output is partial for candidates: {', '.join(sorted(missing))}."
        )
    return True


def _candidate_map(candidates: tuple[LensCandidate, ...]) -> dict[str, LensCandidate]:
    candidates_by_id: dict[str, LensCandidate] = {}
    for candidate in candidates:
        if candidate.candidate_id in candidates_by_id:
            raise OrchestratorError(
                f"Cannot resume: duplicate candidate ID {candidate.candidate_id}."
            )
        candidates_by_id[candidate.candidate_id] = candidate
    return candidates_by_id


__all__ = [
    "critic_complete",
    "critic_result_from_audit",
    "ensure_stage_completed",
    "execution_result_from_audit",
    "load_resume_document",
    "reconciliation_result_from_audit",
    "reconciler_complete",
    "transition_manifest",
    "validate_resume_chunks",
    "validate_resume_plan",
    "verification_result_from_audit",
    "verifier_complete",
]
