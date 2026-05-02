from __future__ import annotations

from extractor.contracts import Chunk, ExtractionPlan, RejectionReason
from extractor.contracts.models import LensName
from extractor.llm import Accepted, Complaints, ItemComplaint, LLMRetryMergeError
from extractor.executor.materialization import build_candidate
from extractor.executor.models import (
    ExecutorCandidateBatch,
    ExtractedCandidatePayload,
)
from extractor.executor.normalization import prepare_candidate_payload
from extractor.executor.policies import candidate_rejection_reasons


def validate_executor_batch(
    *,
    output: ExecutorCandidateBatch,
    lens: LensName,
    chunk: Chunk,
    category_fields: dict[str, frozenset[str]],
    plan: ExtractionPlan,
) -> Accepted[ExecutorCandidateBatch] | Complaints:
    complaints: list[ItemComplaint] = []
    for index, payload in enumerate(output.candidates):
        candidate_payload, resolution = prepare_candidate_payload(
            payload=payload,
            chunk=chunk,
        )
        candidate = build_candidate(
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
            *candidate_rejection_reasons(
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


def merge_executor_batch(
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
        raise LLMRetryMergeError(f"executor retry index out of range: {bad_indices}")
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


__all__ = ["merge_executor_batch", "validate_executor_batch"]
