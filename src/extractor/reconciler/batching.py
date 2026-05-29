from __future__ import annotations

from extractor.canonical_values import (
    canonical_value_key_for_candidate,
    canonical_value_key_identity,
)
from extractor.contracts import LensCandidate
from extractor.llm import Accepted, Complaints, ItemComplaint
from extractor.reconciler.errors import ReconcilerError
from extractor.reconciler.models import (
    ReconciledGroupPayload,
    ReconciliationBatch,
    RejectedCandidateDecision,
)


def expand_reconciliation_batch_ids(
    *,
    batch: ReconciliationBatch,
    candidates_by_view_id: dict[str, LensCandidate],
) -> ReconciliationBatch:
    groups: list[ReconciledGroupPayload] = []
    for source_candidate_id, contributing_candidate_ids in batch.groups:
        groups.append(
            (
                _full_candidate_id(source_candidate_id, candidates_by_view_id),
                tuple(
                    _full_candidate_id(candidate_id, candidates_by_view_id)
                    for candidate_id in contributing_candidate_ids
                ),
            )
        )

    rejected: list[RejectedCandidateDecision] = []
    for candidate_id, code in batch.rejected:
        rejected.append(
            (
                _full_candidate_id(candidate_id, candidates_by_view_id),
                code,
            )
        )

    return ReconciliationBatch(
        groups=tuple(groups),
        rejected=tuple(rejected),
    )


def validate_reconciliation_batch(
    *,
    batch: ReconciliationBatch,
    candidates_by_view_id: dict[str, LensCandidate],
) -> Accepted[ReconciliationBatch] | Complaints:
    unknown_ids = _unknown_compact_candidate_ids(
        batch=batch,
        candidates_by_view_id=candidates_by_view_id,
    )
    if not unknown_ids:
        conflict_complaints = _same_field_conflict_complaints(
            batch=batch,
            candidates_by_view_id=candidates_by_view_id,
        )
        if conflict_complaints:
            return Complaints(complaints=conflict_complaints)
        return Accepted(output=batch)

    allowed_ids = ", ".join(sorted(candidates_by_view_id))
    return Complaints(
        complaints=(
            ItemComplaint(
                identifier="candidate_ids",
                message=(
                    "Reconciler output referenced candidate IDs that were not "
                    f"in the input candidate list: {', '.join(unknown_ids)}. "
                    "Re-emit the complete reconciliation output using only "
                    f"these candidate IDs: {allowed_ids}."
                ),
            ),
        )
    )


def _same_field_conflict_complaints(
    *,
    batch: ReconciliationBatch,
    candidates_by_view_id: dict[str, LensCandidate],
) -> tuple[ItemComplaint, ...]:
    kept_ids = _kept_compact_candidate_ids(batch)
    omitted_or_rejected_ids = set(candidates_by_view_id) - kept_ids
    complaints: list[ItemComplaint] = []
    for omitted_id in sorted(omitted_or_rejected_ids):
        omitted = candidates_by_view_id[omitted_id]
        conflicting_kept_ids = tuple(
            kept_id
            for kept_id in sorted(kept_ids)
            if _same_field_distinct_value(
                candidates_by_view_id[kept_id],
                omitted,
            )
        )
        if not conflicting_kept_ids:
            continue
        complaints.append(
            ItemComplaint(
                identifier=omitted_id,
                message=(
                    "Candidate was omitted or rejected even though it is a "
                    "same-category/same-field conflicting value. Keep it as a "
                    "separate group unless it is schema-invalid. Conflicting "
                    f"kept candidate IDs: {', '.join(conflicting_kept_ids)}."
                ),
            )
        )
    return tuple(complaints)


def _kept_compact_candidate_ids(batch: ReconciliationBatch) -> set[str]:
    kept_ids: set[str] = set()
    for source_candidate_id, contributing_candidate_ids in batch.groups:
        kept_ids.add(source_candidate_id)
        kept_ids.update(contributing_candidate_ids)
    return kept_ids


def _same_field_distinct_value(first: LensCandidate, second: LensCandidate) -> bool:
    if first.category != second.category or first.field_name != second.field_name:
        return False
    if (
        first.normalization_status != "canonicalized"
        or second.normalization_status != "canonicalized"
    ):
        return False
    return canonical_value_key_identity(
        canonical_value_key_for_candidate(first)
    ) != canonical_value_key_identity(canonical_value_key_for_candidate(second))


def replace_reconciliation_batch(
    prior: ReconciliationBatch,
    retry: ReconciliationBatch,
    bad_ids: frozenset[str],
) -> ReconciliationBatch:
    del prior, bad_ids
    return retry


def _unknown_compact_candidate_ids(
    *,
    batch: ReconciliationBatch,
    candidates_by_view_id: dict[str, LensCandidate],
) -> tuple[str, ...]:
    known_ids = set(candidates_by_view_id)
    referenced_ids: set[str] = set()
    for source_candidate_id, contributing_candidate_ids in batch.groups:
        referenced_ids.add(source_candidate_id)
        referenced_ids.update(contributing_candidate_ids)
    referenced_ids.update(candidate_id for candidate_id, _ in batch.rejected)
    return tuple(sorted(referenced_ids - known_ids))


def _full_candidate_id(
    compact_id: str,
    candidates_by_view_id: dict[str, LensCandidate],
) -> str:
    candidate = candidates_by_view_id.get(compact_id)
    if candidate is None:
        raise ReconcilerError(
            f"reconciler output referenced unknown candidate IDs: {compact_id}"
        )
    return candidate.candidate_id


__all__ = [
    "expand_reconciliation_batch_ids",
    "replace_reconciliation_batch",
    "validate_reconciliation_batch",
]
