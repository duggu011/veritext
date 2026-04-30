from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone

from pydantic import ValidationError

from extractor.audit import AuditStore, CandidateRejection
from extractor.config import ExecutionConfig
from extractor.contracts import (
    Chunk,
    CriticIssue,
    CriticReport,
    ExtractionPlan,
    LensCandidate,
    RejectionReason,
    SourceSpan,
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
from extractor.critic.models import (
    CompactCorrection,
    CriticBatchVerdicts,
    CriticBatchStageInput,
    CriticResult,
    CriticTaskResult,
    CriticVerdict,
)


class CriticError(RuntimeError):
    """Raised when critic inputs cannot be reviewed without violating provenance."""


async def review_candidates(
    *,
    plan: ExtractionPlan,
    chunks: tuple[Chunk, ...],
    candidates: tuple[LensCandidate, ...],
    merged_into: dict[str, str] | None = None,
    merged_candidates: tuple[LensCandidate, ...] = (),
    prompt_loader: PromptLoader,
    llm_client: LLMClient,
    execution_config: ExecutionConfig,
    audit_store: AuditStore | None = None,
) -> CriticResult:
    if not candidates:
        return CriticResult(
            accepted_candidates=(),
            rejected_candidates=(),
            reports=(),
            rejections=(),
        )

    chunks_by_id = _validate_critic_inputs(plan, chunks, candidates)
    semaphore = asyncio.Semaphore(execution_config.max_stage_concurrency)
    batches = _partition_into_batches(candidates, execution_config.critic_batch_size)
    cache_primed = (
        asyncio.Event()
        if len(batches) > 1
        and llm_client.config.provider == "anthropic"
        and llm_client.config.prompt_cache_enabled
        else None
    )
    tasks = [
        _review_batch(
            plan=plan,
            chunk=chunks_by_id[batch[0].chunk_id],
            batch=batch,
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
    accepted_candidates = tuple(
        candidate for result in results for candidate in result.accepted_candidates
    )
    rejected_candidates = tuple(
        candidate for result in results for candidate in result.rejected_candidates
    )
    reports = tuple(report for result in results for report in result.reports)
    rejections = tuple(rejection for result in results for rejection in result.rejections)

    (
        mirrored_accepted,
        mirrored_rejected,
        mirrored_reports,
    ) = await _mirror_merged_critic_reports(
        plan=plan,
        reports=reports,
        merged_into=merged_into or {},
        merged_candidates=merged_candidates,
        audit_store=audit_store,
    )

    return CriticResult(
        accepted_candidates=(*accepted_candidates, *mirrored_accepted),
        rejected_candidates=(*rejected_candidates, *mirrored_rejected),
        reports=(*reports, *mirrored_reports),
        rejections=rejections,
    )


def _partition_into_batches(
    candidates: tuple[LensCandidate, ...],
    batch_size: int,
) -> list[tuple[LensCandidate, ...]]:
    # Group by chunk_id (insertion order) so each batch shares chunk context, then
    # split each group into contiguous slices of at most batch_size.
    by_chunk: dict[str, list[LensCandidate]] = {}
    for candidate in candidates:
        by_chunk.setdefault(candidate.chunk_id, []).append(candidate)
    batches: list[tuple[LensCandidate, ...]] = []
    for group in by_chunk.values():
        for start in range(0, len(group), batch_size):
            batches.append(tuple(group[start : start + batch_size]))
    return batches


async def _review_batch(
    *,
    plan: ExtractionPlan,
    chunk: Chunk,
    batch: tuple[LensCandidate, ...],
    batch_index: int,
    cache_primed: asyncio.Event | None,
    prompt_loader: PromptLoader,
    llm_client: LLMClient,
    audit_store: AuditStore | None,
    semaphore: asyncio.Semaphore,
) -> CriticTaskResult:
    if batch_index > 0 and cache_primed is not None:
        await cache_primed.wait()

    candidate_views, _candidates_by_view_id = build_candidate_view_map(batch)
    stage_input = CriticBatchStageInput(
        schema_card=schema_card_from_plan(plan),
        chunk_view=chunk_view_from_chunk(chunk),
        candidates=candidate_views,
    )
    stable_user_prefix, user_content = split_model_json_before_field(
        stage_input,
        "candidates",
    )
    try:
        async with semaphore:
            result = await llm_client.complete_structured(
                StructuredLLMRequest(
                    run_id=plan.run_id,
                    stage="critic",
                    prompt=prompt_loader.load("critic"),
                    user_content=user_content,
                    stable_user_prefix=stable_user_prefix,
                    tool_name="review_candidates_batch",
                    tool_description=(
                        "Review a batch of executor candidates from one chunk for "
                        "plausibility and corrections."
                    ),
                ),
                output_model=CriticBatchVerdicts,
                audit_store=audit_store,
            )
    finally:
        if batch_index == 0 and cache_primed is not None:
            cache_primed.set()

    verdicts_by_candidate: dict[str, CriticVerdict] = {}
    for verdict in result.output.verdicts:
        # First report wins — the model occasionally repeats an id.
        verdicts_by_candidate.setdefault(verdict.id, verdict)

    accepted_candidates: list[LensCandidate] = []
    rejected_candidates: list[LensCandidate] = []
    reports: list[CriticReport] = []
    rejections: list[CandidateRejection] = []

    for candidate in batch:
        view_id = short_candidate_id(candidate.candidate_id)
        verdict = verdicts_by_candidate.get(view_id)
        if verdict is None:
            reasons = [
                RejectionReason(
                    code="critic_missing_report",
                    message=(
                        "Critic batch response did not include a report for "
                        f"candidate {candidate.candidate_id}."
                    ),
                )
            ]
            rejection = CandidateRejection(
                rejection_id=_stable_missing_rejection_id(
                    candidate=candidate,
                    critic_call_id=result.call_log.call_id,
                    reasons=reasons,
                ),
                run_id=plan.run_id,
                candidate_id=candidate.candidate_id,
                stage="critic",
                reasons=tuple(reasons),
                created_at=datetime.now(timezone.utc),
            )
            if audit_store is not None:
                await audit_store.record_candidate_rejection(rejection)
            rejected_candidates.append(candidate)
            rejections.append(rejection)
            continue

        report, corrected_candidate, validation_reasons = _build_report(
            plan=plan,
            chunk=chunk,
            candidate=candidate,
            verdict=verdict,
            critic_call_id=result.call_log.call_id,
        )
        if audit_store is not None:
            await audit_store.record_critic_report(report)

        if report.accepted:
            accepted_candidates.append(corrected_candidate or candidate)
            reports.append(report)
            continue

        reasons = validation_reasons or _critic_rejection_reasons(report)
        rejection = CandidateRejection(
            rejection_id=_stable_rejection_id(candidate, report, reasons),
            run_id=plan.run_id,
            candidate_id=candidate.candidate_id,
            stage="critic",
            reasons=tuple(reasons),
            created_at=datetime.now(timezone.utc),
        )
        if audit_store is not None:
            await audit_store.record_candidate_rejection(rejection)
        rejected_candidates.append(candidate)
        reports.append(report)
        rejections.append(rejection)

    return CriticTaskResult(
        accepted_candidates=tuple(accepted_candidates),
        rejected_candidates=tuple(rejected_candidates),
        reports=tuple(reports),
        rejections=tuple(rejections),
    )


def _validate_critic_inputs(
    plan: ExtractionPlan,
    chunks: tuple[Chunk, ...],
    candidates: tuple[LensCandidate, ...],
) -> dict[str, Chunk]:
    if not chunks:
        raise CriticError("critic requires chunks for candidate context")

    chunks_by_id: dict[str, Chunk] = {}
    for chunk in chunks:
        if chunk.doc_id != plan.doc_id:
            raise CriticError("chunk doc_id must match extraction plan doc_id")
        chunks_by_id[chunk.chunk_id] = chunk

    category_fields = _approved_category_fields(plan)
    for candidate in candidates:
        if candidate.run_id != plan.run_id:
            raise CriticError("candidate run_id must match extraction plan run_id")
        if candidate.doc_id != plan.doc_id:
            raise CriticError("candidate doc_id must match extraction plan doc_id")
        chunk = chunks_by_id.get(candidate.chunk_id)
        if chunk is None:
            raise CriticError("candidate chunk_id must reference a provided chunk")
        fields = category_fields.get(candidate.category)
        if fields is None or candidate.field_name not in fields:
            raise CriticError("critic candidates must already satisfy the approved schema")
        if not _span_matches_chunk(candidate.source_span, chunk):
            raise CriticError("critic candidates must preserve source spans that match chunk text")
    return chunks_by_id


async def _mirror_merged_critic_reports(
    *,
    plan: ExtractionPlan,
    reports: tuple[CriticReport, ...],
    merged_into: dict[str, str],
    merged_candidates: tuple[LensCandidate, ...],
    audit_store: AuditStore | None,
) -> tuple[tuple[LensCandidate, ...], tuple[LensCandidate, ...], tuple[CriticReport, ...]]:
    if not merged_into:
        return (), (), ()

    reports_by_candidate = {report.candidate_id: report for report in reports}
    merged_candidates_by_id = {
        candidate.candidate_id: candidate for candidate in merged_candidates
    }
    accepted: list[LensCandidate] = []
    rejected: list[LensCandidate] = []
    mirrored_reports: list[CriticReport] = []

    for duplicate_id, primary_id in sorted(merged_into.items()):
        duplicate = merged_candidates_by_id.get(duplicate_id)
        if duplicate is None:
            raise CriticError(f"merged duplicate candidate is missing: {duplicate_id}")
        if duplicate.run_id != plan.run_id or duplicate.doc_id != plan.doc_id:
            raise CriticError("merged duplicate candidate must match extraction plan identity")

        primary_report = reports_by_candidate.get(primary_id)
        if primary_report is None:
            continue

        mirrored_report = _mirror_critic_report(
            primary_report=primary_report,
            duplicate=duplicate,
        )
        mirrored_reports.append(mirrored_report)
        if audit_store is not None:
            await audit_store.record_critic_report(mirrored_report)

        if mirrored_report.accepted:
            accepted.append(mirrored_report.corrected_candidate or duplicate)
        else:
            rejected.append(duplicate)

    return tuple(accepted), tuple(rejected), tuple(mirrored_reports)


def _mirror_critic_report(
    *,
    primary_report: CriticReport,
    duplicate: LensCandidate,
) -> CriticReport:
    corrected_candidate = _mirror_corrected_candidate(
        corrected=primary_report.corrected_candidate,
        duplicate=duplicate,
    )
    return CriticReport(
        report_id=_stable_mirrored_report_id(
            primary_report=primary_report,
            duplicate=duplicate,
        ),
        run_id=duplicate.run_id,
        candidate_id=duplicate.candidate_id,
        critic_call_id=primary_report.critic_call_id,
        plausibility_score=primary_report.plausibility_score,
        accepted=primary_report.accepted,
        issues=primary_report.issues,
        corrected_candidate=corrected_candidate,
    )


def _mirror_corrected_candidate(
    *,
    corrected: LensCandidate | None,
    duplicate: LensCandidate,
) -> LensCandidate | None:
    if corrected is None:
        return None
    return duplicate.model_copy(
        update={
            "category": corrected.category,
            "field_name": corrected.field_name,
            "value": corrected.value,
            "source_span": corrected.source_span.model_copy(
                update={
                    "doc_id": duplicate.doc_id,
                    "chunk_id": duplicate.chunk_id,
                }
            ),
            "confidence": corrected.confidence,
        }
    )


def _build_report(
    *,
    plan: ExtractionPlan,
    chunk: Chunk,
    candidate: LensCandidate,
    verdict: CriticVerdict,
    critic_call_id: str,
) -> tuple[CriticReport, LensCandidate | None, list[RejectionReason]]:
    validation_reasons: list[RejectionReason] = []
    corrected_candidate: LensCandidate | None = None

    if verdict.decision == "accept":
        accepted = True
        plausibility_score = 1.0
        issues: tuple[CriticIssue, ...] = ()
    elif verdict.decision == "reject":
        accepted = False
        plausibility_score = 0.0
        issues = (
            CriticIssue(
                code=_required_code(verdict),
                severity=_severity_for(_required_code(verdict)),
                message=verdict.evidence or _default_message(_required_code(verdict)),
            ),
        )
    else:
        corrected_candidate, structural_reasons = _materialize_correction(
            raw=verdict.correction,
            original=candidate,
            chunk=chunk,
        )
        validation_reasons = list(structural_reasons)
        if corrected_candidate is not None:
            validation_reasons.extend(
                _correction_rejection_reasons(
                    plan=plan,
                    chunk=chunk,
                    original=candidate,
                    corrected=corrected_candidate,
                )
            )
        accepted = not validation_reasons
        plausibility_score = 1.0 if accepted else 0.0
        issues = ()
        if validation_reasons:
            issues = (
                CriticIssue(
                    code="invalid_correction",
                    severity="high",
                    message="Critic correction failed invariant validation.",
                ),
            )
            corrected_candidate = None

    report = CriticReport(
        report_id=_stable_report_id(
            candidate=candidate,
            critic_call_id=critic_call_id,
            plausibility_score=plausibility_score,
            accepted=accepted,
            issues=issues,
            corrected_candidate=corrected_candidate,
        ),
        run_id=plan.run_id,
        candidate_id=candidate.candidate_id,
        critic_call_id=critic_call_id,
        plausibility_score=plausibility_score,
        accepted=accepted,
        issues=issues,
        corrected_candidate=corrected_candidate,
    )
    return report, corrected_candidate, validation_reasons


def _required_code(verdict: CriticVerdict) -> RejectionReasonCode:
    if verdict.code is None:
        raise CriticError("non-accepted critic verdict must include a rejection code")
    return verdict.code


def _severity_for(code: RejectionReasonCode) -> str:
    if code in {
        "invented_span",
        "category_not_approved",
        "schema_violation",
        "invalid_source_offsets",
        "ambiguous_source_span",
    }:
        return "high"
    return "medium"


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


def _materialize_correction(
    *,
    raw: CompactCorrection | None,
    original: LensCandidate,
    chunk: Chunk,
) -> tuple[LensCandidate | None, list[RejectionReason]]:
    """Merge a compact correction delta into a strict LensCandidate.

    Identity and provenance fields come from the original candidate, never from
    the LLM. Bytes and end_char are derived from the selected chunk text.
    """
    if raw is None:
        return None, []

    span_start_char = (
        raw.span_start_char
        if raw.span_start_char is not None
        else original.source_span.start_char
    )
    span_text = raw.span_text if raw.span_text is not None else original.source_span.text

    relative_start = span_start_char - chunk.start_char
    relative_end = relative_start + len(span_text)
    if (
        relative_start < 0
        or relative_end > len(chunk.text)
        or chunk.text[relative_start:relative_end] != span_text
    ):
        return None, [
            RejectionReason(
                code="invented_span",
                message=(
                    "Corrected candidate span_text does not match the chunk "
                    f"slice at start_char {span_start_char}."
                ),
            )
        ]

    end_char = span_start_char + len(span_text)
    prefix_bytes = len(chunk.text[:relative_start].encode("utf-8"))
    text_bytes = len(span_text.encode("utf-8"))
    start_byte = chunk.start_byte + prefix_bytes
    end_byte = start_byte + text_bytes

    candidate_dict = original.model_dump()
    if raw.value is not None:
        candidate_dict["value"] = raw.value
    if raw.category is not None:
        candidate_dict["category"] = raw.category
    if raw.field_name is not None:
        candidate_dict["field_name"] = raw.field_name
    candidate_dict["source_span"] = {
        "doc_id": original.doc_id,
        "chunk_id": original.chunk_id,
        "start_char": span_start_char,
        "end_char": end_char,
        "start_byte": start_byte,
        "end_byte": end_byte,
        "text": span_text,
    }
    try:
        return LensCandidate.model_validate(candidate_dict), []
    except ValidationError as exc:
        message = "; ".join(
            f"{'.'.join(str(p) for p in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ) or "Corrected candidate failed contract validation."
        return None, [
            RejectionReason(
                code="invented_span",
                message=f"Corrected candidate violated invariants: {message}",
            )
        ]


def _correction_rejection_reasons(
    *,
    plan: ExtractionPlan,
    chunk: Chunk,
    original: LensCandidate,
    corrected: LensCandidate | None,
) -> list[RejectionReason]:
    if corrected is None:
        return []

    reasons: list[RejectionReason] = []
    if corrected.candidate_id != original.candidate_id:
        reasons.append(
            RejectionReason(
                code="schema_violation",
                message="Corrected candidate must preserve candidate_id.",
            )
        )
    if corrected.run_id != original.run_id:
        reasons.append(
            RejectionReason(
                code="schema_violation",
                message="Corrected candidate must preserve run_id.",
            )
        )
    if corrected.doc_id != original.doc_id:
        reasons.append(
            RejectionReason(
                code="schema_violation",
                message="Corrected candidate must preserve doc_id.",
            )
        )
    if corrected.chunk_id != original.chunk_id:
        reasons.append(
            RejectionReason(
                code="schema_violation",
                message="Corrected candidate must preserve chunk_id.",
            )
        )
    if corrected.lens != original.lens:
        reasons.append(
            RejectionReason(
                code="schema_violation",
                message="Corrected candidate must preserve lens.",
            )
        )
    if corrected.executor_call_id != original.executor_call_id:
        reasons.append(
            RejectionReason(
                code="schema_violation",
                message="Corrected candidate must preserve executor_call_id.",
            )
        )

    fields = _approved_category_fields(plan).get(corrected.category)
    if fields is None or corrected.field_name not in fields:
        reasons.append(
            RejectionReason(
                code="schema_violation",
                message="Corrected candidate category and field must be approved by the plan.",
            )
        )
    if not _span_matches_chunk(corrected.source_span, chunk):
        reasons.append(
            RejectionReason(
                code="invented_span",
                message="Corrected candidate source span must match the chunk text at its offsets.",
            )
        )
    return reasons


def _critic_rejection_reasons(report: CriticReport) -> list[RejectionReason]:
    if not report.issues:
        return [
            RejectionReason(
                code="critic_rejected",
                message="Critic rejected candidate without a specific issue.",
            )
        ]
    return [
        RejectionReason(
            code="critic_rejected",
            message=f"{issue.severity} issue {issue.code}: {issue.message}",
        )
        for issue in report.issues
    ]


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
    critic_call_id: str,
    plausibility_score: float,
    accepted: bool,
    issues: tuple[CriticIssue, ...],
    corrected_candidate: LensCandidate | None,
) -> str:
    issue_identity = "|".join(
        f"{issue.code}:{issue.severity}:{issue.message}" for issue in issues
    )
    correction_identity = (
        corrected_candidate.model_dump_json() if corrected_candidate is not None else "none"
    )
    identity = "|".join(
        (
            candidate.candidate_id,
            critic_call_id,
            str(plausibility_score),
            str(accepted),
            issue_identity,
            correction_identity,
        )
    )
    return f"critic-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


def _stable_mirrored_report_id(
    *,
    primary_report: CriticReport,
    duplicate: LensCandidate,
) -> str:
    identity = f"{primary_report.report_id}|{duplicate.candidate_id}|mirrored"
    return f"critic-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


def _stable_rejection_id(
    candidate: LensCandidate,
    report: CriticReport,
    reasons: list[RejectionReason],
) -> str:
    reason_identity = "|".join(f"{reason.code}:{reason.message}" for reason in reasons)
    identity = f"{candidate.candidate_id}|{report.report_id}|{reason_identity}"
    return f"rejection-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


def _stable_missing_rejection_id(
    *,
    candidate: LensCandidate,
    critic_call_id: str,
    reasons: list[RejectionReason],
) -> str:
    reason_identity = "|".join(f"{reason.code}:{reason.message}" for reason in reasons)
    identity = f"{candidate.candidate_id}|{critic_call_id}|missing|{reason_identity}"
    return f"rejection-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


__all__ = ["CriticError", "review_candidates"]
