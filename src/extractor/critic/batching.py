from __future__ import annotations

from extractor.contracts import Chunk, ExtractionPlan, LensCandidate, RejectionReason
from extractor.llm import Accepted, Complaints, ItemComplaint, LLMRetryMergeError
from extractor.critic.checks import contradicted_rejection_reasons
from extractor.critic.corrections import (
    correction_rejection_reasons,
    materialize_correction,
    should_preserve_original_for_correction,
)
from extractor.critic.models import CriticBatchVerdicts, CriticVerdict


def partition_into_batches(
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


def validate_critic_batch(
    *,
    output: CriticBatchVerdicts,
    plan: ExtractionPlan,
    chunk: Chunk,
    candidates_by_view_id: dict[str, LensCandidate],
) -> Accepted[CriticBatchVerdicts] | Complaints:
    expected_ids = frozenset(candidates_by_view_id)
    seen_ids = {verdict.id for verdict in output.verdicts}
    complaints: list[ItemComplaint] = []

    for verdict_id in sorted(seen_ids - expected_ids):
        complaints.append(
            ItemComplaint(
                identifier=verdict_id,
                message=_format_critic_unknown_id_complaint(
                    verdict_id=verdict_id,
                    expected_ids=expected_ids,
                ),
            )
        )
    for verdict_id in sorted(expected_ids - seen_ids):
        complaints.append(
            ItemComplaint(
                identifier=verdict_id,
                message=_format_critic_missing_verdict_complaint(verdict_id),
            )
        )

    for verdict in output.verdicts:
        if verdict.id not in expected_ids:
            continue
        candidate = candidates_by_view_id[verdict.id]
        if verdict.decision == "reject":
            reasons = contradicted_rejection_reasons(
                plan=plan,
                chunk=chunk,
                candidate=candidate,
                verdict=verdict,
            )
            if reasons:
                complaints.append(
                    ItemComplaint(
                        identifier=verdict.id,
                        message=_format_critic_rejection_complaint(
                            verdict=verdict,
                            reasons=reasons,
                        ),
                    )
                )
            continue
        if verdict.decision != "correct":
            continue
        corrected, structural_reasons = materialize_correction(
            raw=verdict.correction,
            original=candidate,
            chunk=chunk,
        )
        reasons: list[RejectionReason] = list(structural_reasons)
        if corrected is not None:
            reasons.extend(
                correction_rejection_reasons(
                    plan=plan,
                    chunk=chunk,
                    original=candidate,
                    corrected=corrected,
                )
            )
        if should_preserve_original_for_correction(
            plan=plan,
            chunk=chunk,
            original=candidate,
            corrected=corrected,
            reasons=reasons,
        ):
            reasons = []
        if reasons:
            complaints.append(
                ItemComplaint(
                    identifier=verdict.id,
                    message=_format_critic_correction_complaint(
                        verdict=verdict,
                        reasons=reasons,
                    ),
                )
            )

    if complaints:
        return Complaints(complaints=tuple(complaints))
    return Accepted(output=output)


def merge_critic_batch(
    *,
    prior: CriticBatchVerdicts,
    retry: CriticBatchVerdicts,
    bad_ids: frozenset[str],
    expected_ids: tuple[str, ...],
) -> CriticBatchVerdicts:
    expected_id_set = frozenset(expected_ids)
    expected_bad_ids = bad_ids & expected_id_set
    fixes = {verdict.id: verdict for verdict in retry.verdicts}
    if len(fixes) != len(retry.verdicts):
        raise LLMRetryMergeError("critic retry returned duplicate verdict ids")
    if set(fixes) != expected_bad_ids:
        raise LLMRetryMergeError(
            "critic retry id mismatch: expected "
            f"{sorted(expected_bad_ids)}, got {sorted(fixes)}"
        )

    merged: list[CriticVerdict] = []
    merged_ids: set[str] = set()
    for verdict in prior.verdicts:
        if verdict.id not in expected_id_set:
            continue
        fixed = fixes.get(verdict.id)
        if fixed is not None:
            merged.append(fixed)
            merged_ids.add(fixed.id)
        else:
            merged.append(verdict)
            merged_ids.add(verdict.id)

    for verdict_id in expected_ids:
        if verdict_id in fixes and verdict_id not in merged_ids:
            merged.append(fixes[verdict_id])

    return CriticBatchVerdicts(verdicts=tuple(merged))


def _format_critic_unknown_id_complaint(
    *,
    verdict_id: str,
    expected_ids: frozenset[str],
) -> str:
    expected = ", ".join(sorted(expected_ids))
    return (
        f"Verdict id {verdict_id!r} was rejected.\n"
        f"You returned: id={verdict_id!r}.\n"
        f"Constraint violated: critic verdict ids must be one of: {expected}.\n"
        "Action: re-emit ONLY this item with a valid id from the input "
        "candidates, or omit it if it does not correspond to an input candidate."
    )


def _format_critic_missing_verdict_complaint(verdict_id: str) -> str:
    return (
        f"Verdict id {verdict_id!r} was missing.\n"
        "You returned: no verdict for this input candidate.\n"
        "Constraint violated: every input candidate must have exactly one critic verdict.\n"
        f"Action: re-emit ONLY this missing verdict using id={verdict_id!r}."
    )


def _format_critic_correction_complaint(
    *,
    verdict: CriticVerdict,
    reasons: list[RejectionReason],
) -> str:
    correction = (
        None
        if verdict.correction is None
        else verdict.correction.model_dump(mode="json")
    )
    constraint = "; ".join(reason.message for reason in reasons)
    return (
        f"Verdict id {verdict.id!r} was rejected.\n"
        f"You returned: decision={verdict.decision!r}, code={verdict.code!r}, "
        f"evidence={verdict.evidence!r}, correction={correction!r}.\n"
        f"Constraint violated: {constraint}.\n"
        "Action: re-emit ONLY this verdict with a valid decision/correction. "
        "If correcting, the correction must preserve candidate identity and its "
        "span_text must match chunk.text at span_start_char."
    )


def _format_critic_rejection_complaint(
    *,
    verdict: CriticVerdict,
    reasons: list[RejectionReason],
) -> str:
    constraint = "; ".join(reason.message for reason in reasons)
    return (
        f"Verdict id {verdict.id!r} was rejected.\n"
        f"You returned: decision={verdict.decision!r}, code={verdict.code!r}, "
        f"evidence={verdict.evidence!r}.\n"
        f"Constraint violated: {constraint}.\n"
        "Action: re-emit ONLY this verdict. Accept if the candidate is valid; "
        "otherwise reject using a reason that is not contradicted by the input "
        "schema, offsets, and span_text."
    )


__all__ = [
    "merge_critic_batch",
    "partition_into_batches",
    "validate_critic_batch",
]
