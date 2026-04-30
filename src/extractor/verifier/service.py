from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone

from extractor.audit import AuditStore, CandidateRejection
from extractor.config import ExecutionConfig
from extractor.contracts import (
    Chunk,
    CriticReport,
    ExtractionPlan,
    LensCandidate,
    RejectionReason,
    SourceSpan,
    VerifierReport,
)
from extractor.contracts.models import RejectionReasonCode
from extractor.llm import LLMClient, PromptLoader, StructuredLLMRequest
from extractor.llm.payloads import split_model_json_before_field
from extractor.llm.views import (
    build_candidate_view_map,
    chunk_view_from_chunk,
    schema_card_from_plan,
    short_candidate_id,
)
from extractor.verifier.models import (
    CriticSummary,
    VerificationResult,
    VerifierBatchItem,
    VerifierBatchVerdicts,
    VerifierBatchStageInput,
    VerifierTaskResult,
    VerifierVerdict,
)


class VerifierError(RuntimeError):
    """Raised when verifier inputs lack auditable critic provenance."""


async def verify_candidates(
    *,
    plan: ExtractionPlan,
    chunks: tuple[Chunk, ...],
    candidates: tuple[LensCandidate, ...],
    critic_reports: tuple[CriticReport, ...],
    prompt_loader: PromptLoader,
    llm_client: LLMClient,
    execution_config: ExecutionConfig,
    audit_store: AuditStore | None = None,
) -> VerificationResult:
    if not candidates:
        return VerificationResult(
            accepted_candidates=(),
            rejected_candidates=(),
            reports=(),
            rejections=(),
        )

    chunks_by_id, reports_by_candidate_id = _validate_verifier_inputs(
        plan=plan,
        chunks=chunks,
        candidates=candidates,
        critic_reports=critic_reports,
    )
    semaphore = asyncio.Semaphore(execution_config.max_stage_concurrency)
    batches = _partition_into_batches(candidates, execution_config.verifier_batch_size)
    cache_primed = (
        asyncio.Event()
        if len(batches) > 1
        and llm_client.config.provider == "anthropic"
        and llm_client.config.prompt_cache_enabled
        else None
    )
    tasks = [
        _verify_batch(
            plan=plan,
            chunk=chunks_by_id[batch[0].chunk_id],
            batch=batch,
            critic_reports_by_candidate=reports_by_candidate_id,
            batch_index=batch_index,
            cache_primed=cache_primed,
            prompt_loader=prompt_loader,
            llm_client=llm_client,
            audit_store=audit_store,
            semaphore=semaphore,
        )
        for batch_index, batch in enumerate(batches)
    ]
    results = await asyncio.gather(*tasks)

    return VerificationResult(
        accepted_candidates=tuple(
            candidate for result in results for candidate in result.accepted_candidates
        ),
        rejected_candidates=tuple(
            candidate for result in results for candidate in result.rejected_candidates
        ),
        reports=tuple(report for result in results for report in result.reports),
        rejections=tuple(rejection for result in results for rejection in result.rejections),
    )


def _partition_into_batches(
    candidates: tuple[LensCandidate, ...],
    batch_size: int,
) -> list[tuple[LensCandidate, ...]]:
    by_chunk: dict[str, list[LensCandidate]] = {}
    for candidate in candidates:
        by_chunk.setdefault(candidate.chunk_id, []).append(candidate)
    batches: list[tuple[LensCandidate, ...]] = []
    for group in by_chunk.values():
        for start in range(0, len(group), batch_size):
            batches.append(tuple(group[start : start + batch_size]))
    return batches


async def _verify_batch(
    *,
    plan: ExtractionPlan,
    chunk: Chunk,
    batch: tuple[LensCandidate, ...],
    critic_reports_by_candidate: dict[str, CriticReport],
    batch_index: int,
    cache_primed: asyncio.Event | None,
    prompt_loader: PromptLoader,
    llm_client: LLMClient,
    audit_store: AuditStore | None,
    semaphore: asyncio.Semaphore,
) -> VerifierTaskResult:
    candidate_views, _candidates_by_view_id = build_candidate_view_map(batch)
    items = tuple(
        VerifierBatchItem(
            candidate=candidate_view,
            critic_summary=CriticSummary(
                accepted=critic_reports_by_candidate[candidate.candidate_id].accepted
            ),
        )
        for candidate, candidate_view in zip(batch, candidate_views, strict=True)
    )
    if batch_index > 0 and cache_primed is not None:
        await cache_primed.wait()

    stage_input = VerifierBatchStageInput(
        schema_card=schema_card_from_plan(plan),
        chunk_view=chunk_view_from_chunk(chunk),
        items=items,
    )
    stable_user_prefix, user_content = split_model_json_before_field(
        stage_input,
        "items",
    )
    try:
        async with semaphore:
            result = await llm_client.complete_structured(
                StructuredLLMRequest(
                    run_id=plan.run_id,
                    stage="verifier",
                    prompt=prompt_loader.load("verifier"),
                    user_content=user_content,
                    stable_user_prefix=stable_user_prefix,
                    tool_name="verify_candidates_batch",
                    tool_description=(
                        "Verify a batch of critic-accepted candidates from one chunk "
                        "against source and schema."
                    ),
                ),
                output_model=VerifierBatchVerdicts,
                audit_store=audit_store,
            )
    finally:
        if batch_index == 0 and cache_primed is not None:
            cache_primed.set()

    verdicts_by_candidate: dict[str, VerifierVerdict] = {}
    for verdict in result.output.verdicts:
        verdicts_by_candidate.setdefault(verdict.id, verdict)

    accepted_candidates: list[LensCandidate] = []
    rejected_candidates: list[LensCandidate] = []
    reports: list[VerifierReport] = []
    rejections: list[CandidateRejection] = []

    for candidate in batch:
        view_id = short_candidate_id(candidate.candidate_id)
        verdict = verdicts_by_candidate.get(view_id)
        if verdict is None:
            reasons = (
                RejectionReason(
                    code="verifier_missing_report",
                    message=(
                        "Verifier batch response did not include a report for "
                        f"candidate {candidate.candidate_id}."
                    ),
                ),
            )
            report = VerifierReport(
                report_id=_stable_missing_report_id(
                    candidate=candidate,
                    verifier_call_id=result.call_log.call_id,
                    reasons=reasons,
                ),
                run_id=plan.run_id,
                candidate_id=candidate.candidate_id,
                verifier_call_id=result.call_log.call_id,
                span_verified=False,
                category_verified=False,
                alignment_score=0.0,
                accepted=False,
                rejection_reasons=reasons,
            )
            if audit_store is not None:
                await audit_store.record_verifier_report(report)
            rejection = CandidateRejection(
                rejection_id=_stable_rejection_id(candidate, report),
                run_id=plan.run_id,
                candidate_id=candidate.candidate_id,
                stage="verifier",
                reasons=reasons,
                created_at=datetime.now(timezone.utc),
            )
            if audit_store is not None:
                await audit_store.record_candidate_rejection(rejection)
            rejected_candidates.append(candidate)
            reports.append(report)
            rejections.append(rejection)
            continue

        report = _build_report(
            plan=plan,
            chunk=chunk,
            candidate=candidate,
            verdict=verdict,
            verifier_call_id=result.call_log.call_id,
        )
        if audit_store is not None:
            await audit_store.record_verifier_report(report)

        if report.accepted:
            accepted_candidates.append(candidate)
            reports.append(report)
            continue

        rejection = CandidateRejection(
            rejection_id=_stable_rejection_id(candidate, report),
            run_id=plan.run_id,
            candidate_id=candidate.candidate_id,
            stage="verifier",
            reasons=report.rejection_reasons,
            created_at=datetime.now(timezone.utc),
        )
        if audit_store is not None:
            await audit_store.record_candidate_rejection(rejection)
        rejected_candidates.append(candidate)
        reports.append(report)
        rejections.append(rejection)

    return VerifierTaskResult(
        accepted_candidates=tuple(accepted_candidates),
        rejected_candidates=tuple(rejected_candidates),
        reports=tuple(reports),
        rejections=tuple(rejections),
    )


def _validate_verifier_inputs(
    *,
    plan: ExtractionPlan,
    chunks: tuple[Chunk, ...],
    candidates: tuple[LensCandidate, ...],
    critic_reports: tuple[CriticReport, ...],
) -> tuple[dict[str, Chunk], dict[str, CriticReport]]:
    if not chunks:
        raise VerifierError("verifier requires chunks for candidate context")

    chunks_by_id: dict[str, Chunk] = {}
    for chunk in chunks:
        if chunk.doc_id != plan.doc_id:
            raise VerifierError("chunk doc_id must match extraction plan doc_id")
        chunks_by_id[chunk.chunk_id] = chunk

    accepted_reports: dict[str, CriticReport] = {}
    for report in critic_reports:
        if report.run_id != plan.run_id:
            raise VerifierError("critic report run_id must match extraction plan run_id")
        if not report.accepted:
            continue
        if report.candidate_id in accepted_reports:
            raise VerifierError("verifier requires exactly one accepted critic report per candidate")
        accepted_reports[report.candidate_id] = report

    for candidate in candidates:
        if candidate.run_id != plan.run_id:
            raise VerifierError("candidate run_id must match extraction plan run_id")
        if candidate.doc_id != plan.doc_id:
            raise VerifierError("candidate doc_id must match extraction plan doc_id")
        if candidate.chunk_id not in chunks_by_id:
            raise VerifierError("candidate chunk_id must reference a provided chunk")

        report = accepted_reports.get(candidate.candidate_id)
        if report is None:
            raise VerifierError("candidate must have an accepted critic report before verification")
        if report.corrected_candidate is not None and report.corrected_candidate != candidate:
            raise VerifierError("candidate must match the accepted critic correction")
    return chunks_by_id, accepted_reports


def _build_report(
    *,
    plan: ExtractionPlan,
    chunk: Chunk,
    candidate: LensCandidate,
    verdict: VerifierVerdict,
    verifier_call_id: str,
) -> VerifierReport:
    deterministic_reasons = _deterministic_rejection_reasons(
        plan=plan,
        chunk=chunk,
        candidate=candidate,
    )
    rejection_reasons = _merged_rejection_reasons(
        (
            *_llm_rejection_reasons(verdict),
            *deterministic_reasons,
        )
    )
    span_verified = not any(
        reason.code in {"invented_span", "invalid_source_offsets", "ambiguous_source_span"}
        for reason in rejection_reasons
    )
    category_verified = not any(
        reason.code in {"category_not_approved", "schema_violation"}
        for reason in rejection_reasons
    )
    accepted = (
        verdict.decision == "accept"
        and span_verified
        and category_verified
        and not rejection_reasons
    )
    if not accepted and not rejection_reasons:
        rejection_reasons = (
            RejectionReason(
                code="verifier_rejected",
                message="Verifier rejected candidate without a specific reason.",
            ),
        )
    alignment_score = 1.0 if accepted else 0.0

    return VerifierReport(
        report_id=_stable_report_id(
            candidate=candidate,
            verifier_call_id=verifier_call_id,
            span_verified=span_verified,
            category_verified=category_verified,
            alignment_score=alignment_score,
            accepted=accepted,
            rejection_reasons=rejection_reasons,
        ),
        run_id=plan.run_id,
        candidate_id=candidate.candidate_id,
        verifier_call_id=verifier_call_id,
        span_verified=span_verified,
        category_verified=category_verified,
        alignment_score=alignment_score,
        accepted=accepted,
        rejection_reasons=() if accepted else rejection_reasons,
    )


def _deterministic_rejection_reasons(
    *,
    plan: ExtractionPlan,
    chunk: Chunk,
    candidate: LensCandidate,
) -> tuple[RejectionReason, ...]:
    reasons: list[RejectionReason] = []
    fields = _approved_category_fields(plan).get(candidate.category)
    if fields is None:
        reasons.append(
            RejectionReason(
                code="category_not_approved",
                message=f"Category is not approved for this extraction plan: {candidate.category}",
            )
        )
    elif candidate.field_name not in fields:
        reasons.append(
            RejectionReason(
                code="schema_violation",
                message=(
                    f"Field {candidate.field_name} is not approved for category "
                    f"{candidate.category}"
                ),
            )
        )

    if not _span_matches_chunk(candidate.source_span, chunk):
        reasons.append(
            RejectionReason(
                code="invented_span",
                message="Candidate source span does not match the chunk text at the provided offsets.",
            )
        )
    return tuple(reasons)


def _llm_rejection_reasons(verdict: VerifierVerdict) -> tuple[RejectionReason, ...]:
    if verdict.decision == "accept":
        return ()
    code = _required_code(verdict)
    return (
        RejectionReason(
            code=code,
            message=verdict.evidence or _default_message(code),
        ),
    )


def _required_code(verdict: VerifierVerdict) -> RejectionReasonCode:
    if verdict.code is None:
        raise VerifierError("rejected verifier verdict must include a rejection code")
    return verdict.code


def _default_message(code: RejectionReasonCode) -> str:
    messages = {
        "invalid_source_offsets": "Candidate source offsets are not valid for the source chunk.",
        "invented_span": "Candidate value is not grounded in the selected source span.",
        "category_not_approved": "Candidate category is not approved by the extraction schema.",
        "critic_rejected": "Critic rejected the candidate.",
        "verifier_rejected": "Verifier rejected the candidate.",
        "reconciler_rejected": "Reconciler rejected the candidate.",
        "schema_violation": "Candidate category or field does not match the approved schema.",
        "ambiguous_source_span": "Candidate source span is ambiguous within the source chunk.",
        "duplicate_candidate": "Candidate duplicates another candidate selected for review.",
    }
    return messages[code]


def _merged_rejection_reasons(
    reasons: tuple[RejectionReason, ...],
) -> tuple[RejectionReason, ...]:
    merged: list[RejectionReason] = []
    seen: set[tuple[str, str]] = set()
    for reason in reasons:
        key = (reason.code, reason.message)
        if key not in seen:
            merged.append(reason)
            seen.add(key)
    return tuple(merged)


def _span_matches_chunk(source_span: SourceSpan, chunk: Chunk) -> bool:
    if source_span.start_char < chunk.start_char or source_span.end_char > chunk.end_char:
        return False
    if source_span.start_byte < chunk.start_byte or source_span.end_byte > chunk.end_byte:
        return False

    relative_start_char = source_span.start_char - chunk.start_char
    relative_end_char = source_span.end_char - chunk.start_char
    relative_start_byte = source_span.start_byte - chunk.start_byte
    relative_end_byte = source_span.end_byte - chunk.start_byte
    chunk_bytes = chunk.text.encode("utf-8")
    return (
        chunk.text[relative_start_char:relative_end_char] == source_span.text
        and chunk_bytes[relative_start_byte:relative_end_byte] == source_span.text.encode("utf-8")
    )


def _approved_category_fields(plan: ExtractionPlan) -> dict[str, frozenset[str]]:
    return {
        category.name: frozenset(field.name for field in category.fields)
        for category in plan.approved_categories
    }


def _stable_report_id(
    *,
    candidate: LensCandidate,
    verifier_call_id: str,
    span_verified: bool,
    category_verified: bool,
    alignment_score: float,
    accepted: bool,
    rejection_reasons: tuple[RejectionReason, ...],
) -> str:
    reason_identity = "|".join(f"{reason.code}:{reason.message}" for reason in rejection_reasons)
    identity = "|".join(
        (
            candidate.candidate_id,
            verifier_call_id,
            str(span_verified),
            str(category_verified),
            str(alignment_score),
            str(accepted),
            reason_identity,
        )
    )
    return f"verifier-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


def _stable_missing_report_id(
    *,
    candidate: LensCandidate,
    verifier_call_id: str,
    reasons: tuple[RejectionReason, ...],
) -> str:
    reason_identity = "|".join(f"{reason.code}:{reason.message}" for reason in reasons)
    identity = f"{candidate.candidate_id}|{verifier_call_id}|missing|{reason_identity}"
    return f"verifier-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


def _stable_rejection_id(candidate: LensCandidate, report: VerifierReport) -> str:
    reason_identity = "|".join(
        f"{reason.code}:{reason.message}" for reason in report.rejection_reasons
    )
    identity = f"{candidate.candidate_id}|{report.report_id}|{reason_identity}"
    return f"rejection-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


__all__ = ["VerifierError", "verify_candidates"]
