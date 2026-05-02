from __future__ import annotations

import asyncio
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import cast

from extractor.audit import AuditStore, CandidateRejection
from extractor.config import ExecutionConfig
from extractor.contracts import (
    Chunk,
    ExtractionPlan,
    LensCandidate,
    RejectionReason,
    SourceSpan,
)
from extractor.contracts.models import LLMStage, LensName
from extractor.llm import (
    Accepted,
    Complaints,
    ItemComplaint,
    LLMClient,
    LLMRetryMergeError,
    PromptLoader,
    StructuredLLMRequest,
)
from extractor.llm.payloads import split_model_json_before_field
from extractor.llm.views import chunk_view_from_chunk, schema_card_from_plan
from extractor.executor.errors import ExecutorError
from extractor.executor.ids import stable_candidate_id, stable_rejection_id
from extractor.executor.models import (
    ExecutionResult,
    ExecutorCandidateBatch,
    ExecutorStageInput,
    ExecutorTaskResult,
    ExtractedCandidatePayload,
)
from extractor.executor.validation import validate_executor_inputs


@dataclass(frozen=True)
class SourceTextResolution:
    start_char: int
    source_text: str
    rejection_reasons: tuple[RejectionReason, ...] = ()


def _trace_enabled() -> bool:
    return os.environ.get("EXTRACTOR_LLM_TRACE", "1") not in {"0", "false", "False", ""}


def _print_executor_outcomes(
    *,
    lens: LensName,
    chunk: Chunk,
    call_id: str,
    outcomes: list[tuple[LensCandidate, tuple[RejectionReason, ...], int | None]],
) -> None:
    if not _trace_enabled() or not outcomes:
        return
    accepted = sum(1 for _, reasons, _ in outcomes if not reasons)
    rejected = len(outcomes) - accepted
    corrected = sum(1 for _, _, corrected_from in outcomes if corrected_from is not None)
    lines = [
        "",
        f" -> EXECUTOR.OUTCOMES | lens={lens} chunk={chunk.chunk_id} call={call_id} "
        f"accepted={accepted} rejected={rejected} corrected={corrected}",
    ]
    for candidate, reasons, corrected_from in outcomes:
        verdict = "PASS" if not reasons else "REJECT"
        snippet = candidate.source_span.text.replace("\n", " ")
        if len(snippet) > 80:
            snippet = snippet[:77] + "..."
        suffix = (
            f"  (auto-corrected from @{corrected_from})"
            if corrected_from is not None
            else ""
        )
        head = (
            f"   [{verdict}] {candidate.candidate_id} "
            f"{candidate.category}.{candidate.field_name} "
            f"@{candidate.source_span.start_char} {snippet!r}{suffix}"
        )
        lines.append(head)
        for reason in reasons:
            lines.append(f"          - {reason.code}: {reason.message}")
    print("\n".join(lines), file=sys.stderr, flush=True)


async def execute_plan(
    *,
    plan: ExtractionPlan,
    chunks: tuple[Chunk, ...],
    prompt_loader: PromptLoader,
    llm_client: LLMClient,
    execution_config: ExecutionConfig,
    audit_store: AuditStore | None = None,
) -> ExecutionResult:
    validate_executor_inputs(plan, chunks)

    semaphore = asyncio.Semaphore(execution_config.max_chunk_concurrency)
    prompt_cache_allowed = len(chunks) > 1
    max_retries = max(execution_config.max_llm_attempts - 1, 0)
    tasks = [
        _execute_lens_chunk(
            plan=plan,
            lens=lens,
            chunk=chunk,
            prompt_cache_allowed=prompt_cache_allowed,
            prompt_loader=prompt_loader,
            llm_client=llm_client,
            audit_store=audit_store,
            semaphore=semaphore,
            max_retries=max_retries,
        )
        for lens in plan.enabled_lenses
        for chunk in chunks
    ]
    results = await asyncio.gather(*tasks)

    return ExecutionResult(
        accepted_candidates=tuple(
            candidate for result in results for candidate in result.accepted_candidates
        ),
        rejected_candidates=tuple(
            candidate for result in results for candidate in result.rejected_candidates
        ),
        rejections=tuple(rejection for result in results for rejection in result.rejections),
    )


async def _execute_lens_chunk(
    *,
    plan: ExtractionPlan,
    lens: LensName,
    chunk: Chunk,
    prompt_cache_allowed: bool,
    prompt_loader: PromptLoader,
    llm_client: LLMClient,
    audit_store: AuditStore | None,
    semaphore: asyncio.Semaphore,
    max_retries: int,
) -> ExecutorTaskResult:
    category_fields = _approved_category_fields(plan)
    async with semaphore:
        stage = cast(LLMStage, f"executor.{lens}")
        stage_input = ExecutorStageInput(
            schema_card=schema_card_from_plan(plan),
            lens=lens,
            chunk_view=chunk_view_from_chunk(chunk),
        )
        stable_user_prefix, user_content = split_model_json_before_field(
            stage_input,
            "chunk_view",
        )

        def validate_batch(
            output: ExecutorCandidateBatch,
        ) -> Accepted[ExecutorCandidateBatch] | Complaints:
            return _validate_executor_batch(
                output=output,
                lens=lens,
                chunk=chunk,
                category_fields=category_fields,
                plan=plan,
            )

        result = await llm_client.complete_structured_with_retry(
            StructuredLLMRequest(
                run_id=plan.run_id,
                stage=stage,
                prompt=prompt_loader.load(stage),
                user_content=user_content,
                stable_user_prefix=stable_user_prefix,
                prompt_cache_allowed=prompt_cache_allowed,
                tool_name=f"extract_{lens}_candidates",
                tool_description=f"Extract {lens} candidates from one chunk.",
            ),
            output_model=ExecutorCandidateBatch,
            audit_store=audit_store,
            validate=validate_batch,
            merge=_merge_executor_batch,
            max_retries=max_retries,
        )

    accepted: list[LensCandidate] = []
    rejected: list[LensCandidate] = []
    rejections: list[CandidateRejection] = []
    outcomes: list[tuple[LensCandidate, tuple[RejectionReason, ...], int | None]] = []

    payloads = _expand_candidate_payloads(
        payloads=result.output.candidates,
        lens=lens,
        chunk=chunk,
        category_fields=category_fields,
    )

    for index, payload in enumerate(payloads):
        original_start_char = payload.start_char
        payload, resolution = _prepare_candidate_payload(payload=payload, chunk=chunk)
        candidate = _build_candidate(
            plan=plan,
            lens=lens,
            chunk=chunk,
            payload=payload,
            start_char=resolution.start_char,
            source_text=resolution.source_text,
            candidate_index=index,
            executor_call_id=result.call_log.call_id,
        )
        reasons = _candidate_rejection_reasons(
            candidate=candidate,
            chunk=chunk,
            category_fields=category_fields,
        )
        reasons = [*resolution.rejection_reasons, *reasons]

        if audit_store is not None:
            await audit_store.record_lens_candidate(candidate)

        corrected_from = (
            original_start_char
            if resolution.start_char != original_start_char
            else None
        )
        outcomes.append((candidate, tuple(reasons), corrected_from))

        if reasons:
            rejection = CandidateRejection(
                rejection_id=stable_rejection_id(candidate, reasons),
                run_id=plan.run_id,
                candidate_id=candidate.candidate_id,
                stage="executor",
                reasons=tuple(reasons),
                created_at=datetime.now(timezone.utc),
            )
            if audit_store is not None:
                await audit_store.record_candidate_rejection(rejection)
            rejected.append(candidate)
            rejections.append(rejection)
        else:
            accepted.append(candidate)

    _print_executor_outcomes(
        lens=lens,
        chunk=chunk,
        call_id=result.call_log.call_id,
        outcomes=outcomes,
    )

    return ExecutorTaskResult(
        accepted_candidates=tuple(accepted),
        rejected_candidates=tuple(rejected),
        rejections=tuple(rejections),
    )


def _validate_executor_batch(
    *,
    output: ExecutorCandidateBatch,
    lens: LensName,
    chunk: Chunk,
    category_fields: dict[str, frozenset[str]],
    plan: ExtractionPlan,
) -> Accepted[ExecutorCandidateBatch] | Complaints:
    complaints: list[ItemComplaint] = []
    for index, payload in enumerate(output.candidates):
        candidate_payload, resolution = _prepare_candidate_payload(
            payload=payload,
            chunk=chunk,
        )
        candidate = _build_candidate(
            plan=plan,
            lens=lens,
            chunk=chunk,
            payload=candidate_payload,
            start_char=resolution.start_char,
            source_text=resolution.source_text,
            candidate_index=index,
            executor_call_id="retry-probe",
        )
        reasons: list[RejectionReason] = [
            *resolution.rejection_reasons,
            *_candidate_rejection_reasons(
                candidate=candidate,
                chunk=chunk,
                category_fields=category_fields,
            ),
        ]
        if reasons:
            complaints.append(
                ItemComplaint(
                    identifier=str(index),
                    message=_format_executor_complaint(
                        index=index,
                        lens=lens,
                        chunk=chunk,
                        payload=payload,
                        reasons=reasons,
                    ),
                )
            )
    if complaints:
        return Complaints(complaints=tuple(complaints))
    return Accepted(output=output)


def _merge_executor_batch(
    prior: ExecutorCandidateBatch,
    retry: ExecutorCandidateBatch,
    bad_ids: frozenset[str],
) -> ExecutorCandidateBatch:
    try:
        bad_indices = sorted(int(identifier) for identifier in bad_ids)
    except ValueError as exc:
        raise LLMRetryMergeError(
            f"executor retry ids must be integer indices: {sorted(bad_ids)}"
        ) from exc
    if len(retry.candidates) != len(bad_indices):
        raise LLMRetryMergeError(
            f"executor retry expected {len(bad_indices)} corrections, "
            f"got {len(retry.candidates)}"
        )
    if bad_indices and (bad_indices[0] < 0 or bad_indices[-1] >= len(prior.candidates)):
        raise LLMRetryMergeError(
            f"executor retry index out of range: {bad_indices}"
        )
    merged = list(prior.candidates)
    for slot, fix in zip(bad_indices, retry.candidates):
        merged[slot] = fix
    return ExecutorCandidateBatch(candidates=tuple(merged))


def _format_executor_complaint(
    *,
    index: int,
    lens: LensName,
    chunk: Chunk,
    payload: ExtractedCandidatePayload,
    reasons: list[RejectionReason],
) -> str:
    relative_start = payload.start_char - chunk.start_char
    relative_end = relative_start + payload.source_length
    if (
        0 <= relative_start <= len(chunk.text)
        and 0 <= relative_end <= len(chunk.text)
        and relative_start <= relative_end
    ):
        claimed_source = chunk.text[relative_start:relative_end]
    else:
        claimed_source = "<offsets out of chunk bounds>"
    constraint = "; ".join(reason.message for reason in reasons)
    return (
        f"Item {index} ({lens}/{payload.category}.{payload.field_name}) was rejected.\n"
        f"You returned: value={payload.value!r}, start_char={payload.start_char}, "
        f"source_length={payload.source_length}, "
        f"chunk_text[start_char-chunk.start_char : ...+source_length]={claimed_source!r}.\n"
        f"Constraint violated: {constraint}.\n"
        f"Action: re-emit ONLY this item with corrected start_char and source_length "
        f"so that chunk.text[start_char - chunk.start_char : "
        f"start_char - chunk.start_char + source_length] is a span that supports the "
        f"emitted value exactly."
    )


def _build_candidate(
    *,
    plan: ExtractionPlan,
    lens: LensName,
    chunk: Chunk,
    payload: ExtractedCandidatePayload,
    start_char: int,
    source_text: str,
    candidate_index: int,
    executor_call_id: str,
) -> LensCandidate:
    end_char = start_char + len(source_text)
    start_byte, end_byte = _derive_byte_offsets(
        chunk=chunk,
        start_char=start_char,
        source_text=source_text,
    )
    source_span = SourceSpan(
        doc_id=plan.doc_id,
        chunk_id=chunk.chunk_id,
        start_char=start_char,
        end_char=end_char,
        start_byte=start_byte,
        end_byte=end_byte,
        text=source_text,
    )
    return LensCandidate(
        candidate_id=stable_candidate_id(
            plan=plan,
            lens=lens,
            chunk=chunk,
            payload=payload,
            start_char=start_char,
            source_text=source_text,
            candidate_index=candidate_index,
        ),
        run_id=plan.run_id,
        doc_id=plan.doc_id,
        chunk_id=chunk.chunk_id,
        lens=lens,
        category=payload.category,
        field_name=payload.field_name,
        value=payload.value,
        source_span=source_span,
        confidence=payload.confidence,
        executor_call_id=executor_call_id,
    )


def _candidate_rejection_reasons(
    *,
    candidate: LensCandidate,
    chunk: Chunk,
    category_fields: dict[str, frozenset[str]],
) -> list[RejectionReason]:
    reasons: list[RejectionReason] = []
    fields = category_fields.get(candidate.category)
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
    return reasons


_SHORT_AMBIGUOUS_SPAN_MAX_CHARS = 24
_OFFSET_REPAIR_FIELDS = frozenset({"metric_name", "period"})
_DERIVED_EVENT_CONFIDENCE = 0.82
_PRIOR_PERIOD_VALUE_RE = re.compile(
    r"(?:[$€£]\s*)?\d[\d,]*(?:\.\d+)?"
    r"(?:\s+(?:million|billion|thousand))?"
    r"\s+in\s+Q[1-4]\s+\d{4}",
    re.IGNORECASE,
)
_LEADING_NUMERIC_RE = re.compile(r"(?:[$€£]\s*)?\d[\d,]*(?:\.\d+)?")
_COMMENCEMENT_EVENT_RE = re.compile(
    r"\b(?:commenced|began|started)\s+(?:commercial\s+)?operations?\b",
    re.IGNORECASE,
)
_ACQUISITION_APPROVAL_EVENT_RE = re.compile(
    r"\bapproved\s+(?:acquiring|(?:the\s+)?acquisition(?:\s+of)?)",
    re.IGNORECASE,
)
_ROLE_LABEL_BY_ATOMIC_FIELD = {
    "forecast_value": "forecast",
    "margin": "margin",
    "target_value": "target",
}
_ROLE_LABELED_ATOMIC_RE = re.compile(
    r"^(?P<value>"
    r"(?:approximately|about|at\s+least|at\s+most|no\s+more\s+than|up\s+to|"
    r"over|under|more\s+than|less\s+than)?\s*"
    r"(?:[$€£]\s*)?"
    r"\d[\d,]*(?:\.\d+)?"
    r"(?:\s*(?:%|percent|basis\s+points|bps))?"
    r"(?:\s+(?:million|billion|thousand|gigawatt-hours|megawatt-hours|"
    r"gigawatts|megawatts|hours|days|months|years))?"
    r"(?:\s+(?:to|-)\s+(?:[$€£]\s*)?\d[\d,]*(?:\.\d+)?"
    r"(?:\s*(?:%|percent))?"
    r"(?:\s+(?:million|billion|thousand|gigawatt-hours|megawatt-hours|"
    r"gigawatts|megawatts|hours|days|months|years))?)?"
    r")\s+(?P<label>forecast|margin|target)\b",
    re.IGNORECASE,
)
_EFFECTIVE_DATE_EVENT_CONTEXT_RE = re.compile(
    r"^(?P<context>\s+(?:Annual|Special|Extraordinary|General|Shareholder|"
    r"Shareholders'?|Stockholder|Stockholders'?|Board)\s+Meeting\b)",
    re.IGNORECASE,
)
_SPEAKER_ROLE_PREFIX_RE = re.compile(
    r"^(?:CEO|CFO|COO|CTO|CIO|CMO|Chair|Chairman|Chairwoman|President|Director|"
    r"Chief Executive Officer)\s+",
    re.IGNORECASE,
)


def _expand_candidate_payloads(
    *,
    payloads: tuple[ExtractedCandidatePayload, ...],
    lens: LensName,
    chunk: Chunk,
    category_fields: dict[str, frozenset[str]],
) -> tuple[ExtractedCandidatePayload, ...]:
    expanded = list(payloads)
    seen = {_candidate_payload_key(payload) for payload in payloads}
    if lens == "event":
        for payload in _derive_event_payloads(
            chunk=chunk,
            category_fields=category_fields,
        ):
            key = _candidate_payload_key(payload)
            if key in seen:
                continue
            seen.add(key)
            expanded.append(payload)
    return tuple(expanded)


def _derive_event_payloads(
    *,
    chunk: Chunk,
    category_fields: dict[str, frozenset[str]],
) -> tuple[ExtractedCandidatePayload, ...]:
    event_categories = tuple(
        category
        for category, fields in category_fields.items()
        if "event_type" in fields
    )
    if not event_categories:
        return ()

    payloads: list[ExtractedCandidatePayload] = []
    for sentence_start, sentence_text in _sentence_spans(chunk.text):
        commencement = _COMMENCEMENT_EVENT_RE.search(sentence_text)
        acquisition_approval = _ACQUISITION_APPROVAL_EVENT_RE.search(sentence_text)
        if commencement is None and acquisition_approval is None:
            continue

        for category in event_categories:
            fields = category_fields[category]
            if commencement is not None:
                payloads.append(
                    _candidate_payload_from_local_span(
                        category=category,
                        field_name="event_type",
                        value="Facility commencement",
                        chunk=chunk,
                        local_start=sentence_start + commencement.start(),
                        source_text=commencement.group(0),
                    )
                )
                if "summary" in fields:
                    payloads.append(
                        _candidate_payload_from_local_span(
                            category=category,
                            field_name="summary",
                            value=sentence_text,
                            chunk=chunk,
                            local_start=sentence_start,
                            source_text=sentence_text,
                        )
                    )
                if "asset_detail" in fields:
                    payloads.append(
                        _candidate_payload_from_local_span(
                            category=category,
                            field_name="asset_detail",
                            value=sentence_text,
                            chunk=chunk,
                            local_start=sentence_start,
                            source_text=sentence_text,
                        )
                    )

            if acquisition_approval is not None:
                payloads.append(
                    _candidate_payload_from_local_span(
                        category=category,
                        field_name="event_type",
                        value="Acquisition approval",
                        chunk=chunk,
                        local_start=sentence_start + acquisition_approval.start(),
                        source_text=acquisition_approval.group(0),
                    )
                )
                if "summary" in fields:
                    payloads.append(
                        _candidate_payload_from_local_span(
                            category=category,
                            field_name="summary",
                            value=sentence_text,
                            chunk=chunk,
                            local_start=sentence_start,
                            source_text=sentence_text,
                        )
                    )

    return tuple(payloads)


def _candidate_payload_from_local_span(
    *,
    category: str,
    field_name: str,
    value: str,
    chunk: Chunk,
    local_start: int,
    source_text: str,
) -> ExtractedCandidatePayload:
    return ExtractedCandidatePayload(
        category=category,
        field_name=field_name,
        value=value,
        start_char=chunk.start_char + local_start,
        source_length=len(source_text),
        confidence=_DERIVED_EVENT_CONFIDENCE,
    )


def _candidate_payload_key(
    payload: ExtractedCandidatePayload,
) -> tuple[str, str, str, int, int]:
    return (
        payload.category,
        payload.field_name,
        _collapse_whitespace(payload.value).casefold(),
        payload.start_char,
        payload.source_length,
    )


def _sentence_spans(text: str) -> tuple[tuple[int, str], ...]:
    spans: list[tuple[int, str]] = []
    start = 0
    index = 0
    while index < len(text):
        char = text[index]
        if char in ".!?" and _is_sentence_terminal(text=text, index=index):
            _append_sentence_span(spans=spans, text=text, start=start, end=index + 1)
            start = index + 1
        elif char == "\n" and index + 1 < len(text) and text[index + 1] == "\n":
            _append_sentence_span(spans=spans, text=text, start=start, end=index)
            start = index + 2
            index += 1
        index += 1
    _append_sentence_span(spans=spans, text=text, start=start, end=len(text))
    return tuple(spans)


def _append_sentence_span(
    *,
    spans: list[tuple[int, str]],
    text: str,
    start: int,
    end: int,
) -> None:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    if start >= end:
        return
    sentence = text[start:end]
    if sentence.lstrip().startswith("#") or not any(char.isalnum() for char in sentence):
        return
    spans.append((start, sentence))


def _is_sentence_terminal(*, text: str, index: int) -> bool:
    if index + 1 < len(text) and not text[index + 1].isspace():
        return False
    prefix = text[:index]
    token_start = max(prefix.rfind(" "), prefix.rfind("\n")) + 1
    token = prefix[token_start:] + "."
    if token.casefold() in {"mr.", "mrs.", "ms.", "dr.", "prof.", "sr.", "jr.", "st."}:
        return False
    if re.search(r"(?:[A-Z]\.){1,}[A-Z]\.$", token):
        return False

    next_index = index + 1
    while next_index < len(text) and text[next_index].isspace():
        next_index += 1
    return next_index >= len(text) or not text[next_index].islower()


def _prepare_candidate_payload(
    *,
    payload: ExtractedCandidatePayload,
    chunk: Chunk,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution]:
    resolution = _resolve_source_text(payload=payload, chunk=chunk)
    return _normalize_resolved_candidate(
        payload=payload,
        resolution=resolution,
        chunk=chunk,
    )


def _resolve_source_text(
    *,
    payload: ExtractedCandidatePayload,
    chunk: Chunk,
) -> SourceTextResolution:
    """Find the safest chunk-backed span for the model's offset/length claim.

    The normal path is a direct chunk slice from start_char + source_length. If
    that span is structurally invalid, a unique value match can repair
    offset/length typos. A valid source slice does not need to contain the value
    literally: values can be semantic labels such as "appointment" while the
    source span contains the sentence that supports that label.
    """
    text = chunk.text
    claimed = _slice_claimed_source_text(payload=payload, chunk=chunk)
    value_matches = _find_value_matches(text, payload.value)

    if claimed is None:
        if len(value_matches) == 1:
            start, end = value_matches[0]
            return SourceTextResolution(
                start_char=chunk.start_char + start,
                source_text=text[start:end],
            )

        reasons = [_invalid_source_length_reason(payload=payload, chunk=chunk)]
        if len(value_matches) > 1:
            reasons.extend(
                _ambiguous_source_span_reason(payload.value, len(value_matches))
            )
        return _fallback_resolution(chunk=chunk, rejection_reasons=tuple(reasons))

    claimed_source = claimed[2]
    claimed_exact_matches = _find_exact_matches(text, claimed_source)
    claimed_is_ambiguous = _is_short_ambiguous_source(
        claimed_source,
        claimed_exact_matches,
    )
    claimed_supports_value = _source_supports_value(claimed_source, payload.value)
    if len(value_matches) == 1 and not claimed_supports_value:
        start, end = value_matches[0]
        return SourceTextResolution(
            start_char=chunk.start_char + start,
            source_text=text[start:end],
        )
    if len(value_matches) > 1 and not claimed_supports_value:
        repaired_match = _select_header_adjacent_value_match(
            payload=payload,
            chunk=chunk,
            matches=value_matches,
        )
        if repaired_match is not None:
            start, end = repaired_match
            return SourceTextResolution(
                start_char=chunk.start_char + start,
                source_text=text[start:end],
            )

    rejection_reasons: tuple[RejectionReason, ...] = ()
    if claimed_is_ambiguous:
        rejection_reasons = _ambiguous_source_span_reason(
            claimed_source,
            len(claimed_exact_matches),
        )
    elif len(value_matches) > 1 and not claimed_supports_value:
        reasons = [_unsupported_value_reason(payload=payload)]
        reasons.extend(_ambiguous_source_span_reason(payload.value, len(value_matches)))
        rejection_reasons = tuple(reasons)

    return SourceTextResolution(
        start_char=payload.start_char,
        source_text=claimed_source,
        rejection_reasons=rejection_reasons,
    )


def _normalize_resolved_candidate(
    *,
    payload: ExtractedCandidatePayload,
    resolution: SourceTextResolution,
    chunk: Chunk,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution]:
    if resolution.rejection_reasons:
        return payload, resolution

    for normalizer in (
        _normalize_label_value,
        _normalize_prior_period_value,
        _normalize_effective_date_event_context,
        _normalize_role_labeled_atomic_value,
        _normalize_condition_value,
        _normalize_notable_qualifier_value,
        _normalize_asset_detail_operational_profile,
        _normalize_speaker_value,
    ):
        normalized = normalizer(payload=payload, resolution=resolution, chunk=chunk)
        if normalized is not None:
            payload, resolution = normalized

    return payload, resolution


def _normalize_label_value(
    *,
    payload: ExtractedCandidatePayload,
    resolution: SourceTextResolution,
    chunk: Chunk,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution] | None:
    del chunk
    if payload.field_name not in {"event_type", "change_type"}:
        return None

    source_key = _collapse_whitespace(resolution.source_text).casefold()
    value_key = _collapse_whitespace(payload.value).casefold()
    key = f"{source_key} {value_key}"

    if "commenced operation" in key and payload.field_name == "event_type":
        return _normalize_to_source_phrase(
            payload=payload,
            resolution=resolution,
            phrase="commenced operation",
            value="Facility commencement",
        )
    if "approved acquiring" in key and payload.field_name == "event_type":
        return _normalize_to_source_phrase(
            payload=payload,
            resolution=resolution,
            phrase="approved acquiring",
            value="Acquisition approval",
        )
    if "appointed" in key and payload.field_name == "change_type":
        return _normalize_to_source_phrase(
            payload=payload,
            resolution=resolution,
            phrase="appointed",
            value="appointment",
        )
    return None


def _normalize_to_source_phrase(
    *,
    payload: ExtractedCandidatePayload,
    resolution: SourceTextResolution,
    phrase: str,
    value: str,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution] | None:
    phrase_start = resolution.source_text.casefold().find(phrase.casefold())
    if phrase_start < 0:
        return None
    source_text = resolution.source_text[phrase_start : phrase_start + len(phrase)]
    return (
        payload.model_copy(update={"value": value}),
        SourceTextResolution(
            start_char=resolution.start_char + phrase_start,
            source_text=source_text,
            rejection_reasons=resolution.rejection_reasons,
        ),
    )


def _normalize_prior_period_value(
    *,
    payload: ExtractedCandidatePayload,
    resolution: SourceTextResolution,
    chunk: Chunk,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution] | None:
    if payload.field_name != "prior_period_value":
        return None

    numeric_key = _leading_numeric_key(payload.value) or _leading_numeric_key(
        resolution.source_text
    )
    if numeric_key is None:
        return None

    current_relative_start = resolution.start_char - chunk.start_char
    matches = [
        match
        for match in _PRIOR_PERIOD_VALUE_RE.finditer(chunk.text)
        if _numeric_keys_match(numeric_key, match.group(0))
    ]
    if not matches:
        return None

    selected = min(matches, key=lambda match: abs(match.start() - current_relative_start))
    source_text = selected.group(0)
    return (
        payload.model_copy(update={"value": source_text}),
        SourceTextResolution(
            start_char=chunk.start_char + selected.start(),
            source_text=source_text,
            rejection_reasons=resolution.rejection_reasons,
        ),
    )


def _leading_numeric_key(text: str) -> str | None:
    match = _LEADING_NUMERIC_RE.search(text)
    if match is None:
        return None
    return _collapse_whitespace(match.group(0)).casefold()


def _numeric_keys_match(expected: str, source: str) -> bool:
    actual = _leading_numeric_key(source)
    return actual == expected if actual is not None else False


def _normalize_condition_value(
    *,
    payload: ExtractedCandidatePayload,
    resolution: SourceTextResolution,
    chunk: Chunk,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution] | None:
    if payload.field_name != "condition":
        return None

    start_char = resolution.start_char
    source_text = resolution.source_text
    if source_text.casefold().startswith("with "):
        start_char += len("with ")
        source_text = source_text[len("with ") :]

    source_text = _extend_condition_clause(
        chunk=chunk,
        start_char=start_char,
        source_text=source_text,
    )
    if start_char == resolution.start_char and source_text == resolution.source_text:
        return None

    return (
        payload.model_copy(update={"value": source_text}),
        SourceTextResolution(
            start_char=start_char,
            source_text=source_text,
            rejection_reasons=resolution.rejection_reasons,
        ),
    )


def _normalize_effective_date_event_context(
    *,
    payload: ExtractedCandidatePayload,
    resolution: SourceTextResolution,
    chunk: Chunk,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution] | None:
    if payload.field_name != "effective_date":
        return None

    relative_end = resolution.start_char - chunk.start_char + len(resolution.source_text)
    if relative_end < 0 or relative_end > len(chunk.text):
        return None
    match = _EFFECTIVE_DATE_EVENT_CONTEXT_RE.match(chunk.text[relative_end:])
    if match is None:
        return None

    source_text = resolution.source_text + match.group("context")
    return (
        payload.model_copy(update={"value": source_text}),
        SourceTextResolution(
            start_char=resolution.start_char,
            source_text=source_text,
            rejection_reasons=resolution.rejection_reasons,
        ),
    )


def _normalize_role_labeled_atomic_value(
    *,
    payload: ExtractedCandidatePayload,
    resolution: SourceTextResolution,
    chunk: Chunk,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution] | None:
    del chunk
    expected_label = _ROLE_LABEL_BY_ATOMIC_FIELD.get(payload.field_name)
    if expected_label is None:
        return None

    leading_ws = len(resolution.source_text) - len(resolution.source_text.lstrip())
    stripped_source = resolution.source_text.lstrip()
    match = _ROLE_LABELED_ATOMIC_RE.match(stripped_source)
    if match is None or match.group("label").casefold() != expected_label:
        return None

    value = match.group("value").strip()
    if value == "":
        return None
    value_start = leading_ws + match.start("value")
    return (
        payload.model_copy(update={"value": value}),
        SourceTextResolution(
            start_char=resolution.start_char + value_start,
            source_text=value,
            rejection_reasons=resolution.rejection_reasons,
        ),
    )


def _normalize_notable_qualifier_value(
    *,
    payload: ExtractedCandidatePayload,
    resolution: SourceTextResolution,
    chunk: Chunk,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution] | None:
    del chunk
    if payload.field_name != "notable_qualifier":
        return None

    matches = _find_value_matches(resolution.source_text, payload.value)
    if len(matches) != 1:
        return None
    start, end = matches[0]
    source_text = resolution.source_text[start:end]
    if source_text == resolution.source_text:
        return None
    return (
        payload.model_copy(update={"value": source_text}),
        SourceTextResolution(
            start_char=resolution.start_char + start,
            source_text=source_text,
            rejection_reasons=resolution.rejection_reasons,
        ),
    )


def _normalize_asset_detail_operational_profile(
    *,
    payload: ExtractedCandidatePayload,
    resolution: SourceTextResolution,
    chunk: Chunk,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution] | None:
    del chunk
    if payload.field_name != "asset_detail":
        return None

    leading_ws = len(resolution.source_text) - len(resolution.source_text.lstrip())
    stripped_source = resolution.source_text.strip()
    verb_match = re.search(
        r"\b(?:operates|operated|owns|owned|includes|comprises)\s+",
        stripped_source,
        flags=re.IGNORECASE,
    )
    if verb_match is None:
        return None

    detail_start = verb_match.end()
    detail_end = len(stripped_source)
    if stripped_source.endswith("."):
        detail_end -= 1
    detail = stripped_source[detail_start:detail_end].strip()
    if not detail or not any(char.isdigit() for char in detail):
        return None

    trimmed_prefix = len(stripped_source[detail_start:detail_end]) - len(
        stripped_source[detail_start:detail_end].lstrip()
    )
    detail_start += trimmed_prefix
    return (
        payload.model_copy(update={"value": detail}),
        SourceTextResolution(
            start_char=resolution.start_char + leading_ws + detail_start,
            source_text=detail,
            rejection_reasons=resolution.rejection_reasons,
        ),
    )


def _extend_condition_clause(
    *,
    chunk: Chunk,
    start_char: int,
    source_text: str,
) -> str:
    relative_end = start_char - chunk.start_char + len(source_text)
    following = chunk.text[relative_end:]
    if not following.startswith(" under "):
        return source_text
    clause_end = len(following)
    for delimiter in (".", ";", "\n"):
        delimiter_index = following.find(delimiter)
        if delimiter_index >= 0:
            clause_end = min(clause_end, delimiter_index)
    return source_text + following[:clause_end]


def _normalize_speaker_value(
    *,
    payload: ExtractedCandidatePayload,
    resolution: SourceTextResolution,
    chunk: Chunk,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution] | None:
    del chunk
    if payload.field_name != "speaker":
        return None

    match = _SPEAKER_ROLE_PREFIX_RE.match(resolution.source_text)
    if match is None:
        return None
    source_text = resolution.source_text[match.end() :]
    if len(source_text.split()) < 2:
        return None
    return (
        payload.model_copy(update={"value": source_text}),
        SourceTextResolution(
            start_char=resolution.start_char + match.end(),
            source_text=source_text,
            rejection_reasons=resolution.rejection_reasons,
        ),
    )


def _slice_claimed_source_text(
    *,
    payload: ExtractedCandidatePayload,
    chunk: Chunk,
) -> tuple[int, int, str] | None:
    relative_start = payload.start_char - chunk.start_char
    relative_end = relative_start + payload.source_length
    if (
        relative_start < 0
        or relative_end > len(chunk.text)
        or payload.source_length == 0
    ):
        return None
    return relative_start, relative_end, chunk.text[relative_start:relative_end]


def _find_value_matches(text: str, value: str) -> list[tuple[int, int]]:
    exact_matches = _find_exact_matches(text, value)
    if exact_matches:
        return [(start, start + len(value)) for start in exact_matches]

    stripped = value.strip()
    if stripped and stripped != value:
        stripped_matches = _find_exact_matches(text, stripped)
        if stripped_matches:
            return [(start, start + len(stripped)) for start in stripped_matches]

    case_insensitive_matches = _find_case_insensitive_matches(text, value)
    if case_insensitive_matches:
        return case_insensitive_matches

    return _find_whitespace_normalized_matches(text, value)


def _select_header_adjacent_value_match(
    *,
    payload: ExtractedCandidatePayload,
    chunk: Chunk,
    matches: list[tuple[int, int]],
) -> tuple[int, int] | None:
    if payload.field_name not in _OFFSET_REPAIR_FIELDS:
        return None

    relative_claimed_start = payload.start_char - chunk.start_char
    body_matches = [
        match for match in matches if not _match_starts_in_markdown_heading(chunk.text, match[0])
    ]
    if not body_matches:
        return None

    after_claim = [match for match in body_matches if match[0] >= relative_claimed_start]
    if after_claim:
        return min(after_claim, key=lambda match: match[0])
    if len(body_matches) == 1:
        return body_matches[0]
    return None


def _source_supports_value(source: str, value: str) -> bool:
    if value in source:
        return True
    stripped = value.strip()
    if stripped and stripped in source:
        return True
    return _collapse_whitespace(value).casefold() in _collapse_whitespace(source).casefold()


def _invalid_source_length_reason(
    *,
    payload: ExtractedCandidatePayload,
    chunk: Chunk,
) -> RejectionReason:
    return RejectionReason(
        code="invalid_source_offsets",
        message=(
            f"Candidate source_length {payload.source_length} at start_char "
            f"{payload.start_char} does not fit chunk "
            f"[{chunk.start_char}, {chunk.end_char})."
        ),
    )


def _unsupported_value_reason(
    *,
    payload: ExtractedCandidatePayload,
) -> RejectionReason:
    return RejectionReason(
        code="invalid_source_offsets",
        message=(
            "Candidate length-based source span does not contain the emitted "
            f"value {payload.value!r}."
        ),
    )


def _fallback_resolution(
    *,
    chunk: Chunk,
    rejection_reasons: tuple[RejectionReason, ...],
) -> SourceTextResolution:
    return SourceTextResolution(
        start_char=chunk.start_char,
        source_text=chunk.text[:1],
        rejection_reasons=rejection_reasons,
    )


def _find_exact_matches(text: str, source: str) -> list[int]:
    matches: list[int] = []
    cursor = 0
    while cursor + len(source) <= len(text):
        idx = text.find(source, cursor)
        if idx < 0:
            break
        matches.append(idx)
        cursor = idx + 1
    return matches


def _is_short_ambiguous_source(source: str, matches: list[int]) -> bool:
    return len(matches) > 1 and len(source) <= _SHORT_AMBIGUOUS_SPAN_MAX_CHARS


def _ambiguous_source_span_reason(
    source: str,
    match_count: int,
) -> tuple[RejectionReason, ...]:
    return (
        RejectionReason(
            code="ambiguous_source_span",
            message=(
                f"Candidate span text {source!r} appears {match_count} times in "
                "the chunk; emit a wider unique source_length to preserve provenance."
            ),
        ),
    )


def _find_case_insensitive_matches(text: str, source: str) -> list[tuple[int, int]]:
    if source == "":
        return []
    return [
        (match.start(), match.end())
        for match in re.finditer(re.escape(source), text, flags=re.IGNORECASE)
    ]


def _match_starts_in_markdown_heading(text: str, start: int) -> bool:
    line_start = text.rfind("\n", 0, start) + 1
    return text[line_start:start].lstrip().startswith("#")


def _find_whitespace_normalized_matches(
    text: str,
    source: str,
) -> list[tuple[int, int]]:
    normalized_source = _collapse_whitespace(source)
    if normalized_source == "" or not any(char.isspace() for char in source):
        return []

    normalized_text, mapping = _normalize_whitespace_with_mapping(text)
    matches: list[tuple[int, int]] = []
    cursor = 0
    while cursor + len(normalized_source) <= len(normalized_text):
        idx = normalized_text.find(normalized_source, cursor)
        if idx < 0:
            break
        start = mapping[idx]
        end = mapping[idx + len(normalized_source) - 1] + 1
        matches.append((start, end))
        cursor = idx + 1
    return matches


def _collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


def _normalize_whitespace_with_mapping(text: str) -> tuple[str, list[int]]:
    normalized: list[str] = []
    mapping: list[int] = []
    in_whitespace = False
    for index, char in enumerate(text):
        if char.isspace():
            if normalized and not in_whitespace:
                normalized.append(" ")
                mapping.append(index)
            in_whitespace = True
            continue
        normalized.append(char)
        mapping.append(index)
        in_whitespace = False

    if normalized and normalized[-1] == " ":
        normalized.pop()
        mapping.pop()
    return "".join(normalized), mapping


def _derive_byte_offsets(
    *,
    chunk: Chunk,
    start_char: int,
    source_text: str,
) -> tuple[int, int]:
    # Caller must have already verified the slice; out-of-range slices return
    # (chunk.start_byte, chunk.start_byte) and are caught by _span_matches_chunk.
    relative_start = start_char - chunk.start_char
    if relative_start < 0 or relative_start > len(chunk.text):
        return chunk.start_byte, chunk.start_byte
    prefix_bytes = len(chunk.text[:relative_start].encode("utf-8"))
    text_bytes = len(source_text.encode("utf-8"))
    return chunk.start_byte + prefix_bytes, chunk.start_byte + prefix_bytes + text_bytes


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


__all__ = ["ExecutorError", "execute_plan"]
