from __future__ import annotations

import hashlib

from datetime import datetime, timezone

from extractor.audit import CandidateRejection
from extractor.canonical_values import canonical_value_key_for_candidate
from extractor.contracts import (
    DedupCluster,
    LensCandidate,
    RejectionReason,
)


def deduplicate_candidates(
    candidates: tuple[LensCandidate, ...],
) -> tuple[tuple[LensCandidate, ...], dict[str, str]]:
    by_key: dict[tuple[object, ...], list[LensCandidate]] = {}
    for candidate in candidates:
        key = _dedup_identity(candidate)
        by_key.setdefault(key, []).append(candidate)

    canonical: list[LensCandidate] = []
    merged_into: dict[str, str] = {}
    for group in sorted(
        by_key.values(),
        key=lambda items: _primary_candidate(items).candidate_id,
    ):
        primary, *duplicates = sorted(group, key=lambda item: item.candidate_id)
        canonical.append(primary)
        for duplicate in duplicates:
            merged_into[duplicate.candidate_id] = primary.candidate_id

    return tuple(canonical), merged_into


def build_dedup_clusters(candidates: tuple[LensCandidate, ...]) -> tuple[DedupCluster, ...]:
    by_key: dict[tuple[object, ...], list[LensCandidate]] = {}
    for candidate in candidates:
        key = _dedup_identity(candidate)
        by_key.setdefault(key, []).append(candidate)

    clusters: list[DedupCluster] = []
    for group in sorted(
        by_key.values(),
        key=lambda items: _primary_candidate(items).candidate_id,
    ):
        sorted_group = tuple(sorted(group, key=lambda item: item.candidate_id))
        if len(sorted_group) == 1:
            continue

        primary, *duplicates = sorted_group
        clusters.append(
            DedupCluster(
                primary_candidate_id=primary.candidate_id,
                merged_candidate_ids=tuple(
                    duplicate.candidate_id for duplicate in duplicates
                ),
                all_candidate_ids=tuple(
                    candidate.candidate_id for candidate in sorted_group
                ),
                canonical_key=canonical_value_key_for_candidate(primary),
                source_span_count=len(
                    {_source_span_identity(candidate) for candidate in sorted_group}
                ),
            )
        )
    return tuple(clusters)


def build_dedup_rejections(
    *,
    run_id: str,
    candidates: tuple[LensCandidate, ...],
    merged_into: dict[str, str],
) -> tuple[CandidateRejection, ...]:
    candidates_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    created_at = datetime.now(timezone.utc)
    rejections: list[CandidateRejection] = []
    for duplicate_id, primary_id in sorted(merged_into.items()):
        if duplicate_id not in candidates_by_id:
            raise ValueError(f"merged duplicate candidate is missing: {duplicate_id}")
        reasons = (
            RejectionReason(
                code="duplicate_candidate",
                message=f"merged_into:{primary_id}",
            ),
        )
        rejections.append(
            CandidateRejection(
                rejection_id=_stable_dedup_rejection_id(
                    duplicate_id=duplicate_id,
                    primary_id=primary_id,
                ),
                run_id=run_id,
                candidate_id=duplicate_id,
                stage="dedup",
                reasons=reasons,
                created_at=created_at,
            )
        )
    return tuple(rejections)


def _stable_dedup_rejection_id(*, duplicate_id: str, primary_id: str) -> str:
    identity = f"{duplicate_id}|{primary_id}|duplicate_candidate"
    return f"rejection-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


def _dedup_identity(candidate: LensCandidate) -> tuple[object, ...]:
    canonical_key = canonical_value_key_for_candidate(candidate)
    identity = (
        candidate.doc_id,
        candidate.lens,
        candidate.category,
        candidate.field_name,
        canonical_key.kind,
        canonical_key.key,
        canonical_key.source,
        canonical_key.policy_id,
        canonical_key.policy_version,
    )
    if candidate.normalization_status == "canonicalized":
        return ("canonical", *identity)
    return ("source_span", *identity, _absolute_source_span_identity(candidate))


def _primary_candidate(candidates: list[LensCandidate]) -> LensCandidate:
    return min(candidates, key=lambda item: item.candidate_id)


def _absolute_source_span_identity(candidate: LensCandidate) -> tuple[object, ...]:
    span = candidate.source_span
    return (
        span.doc_id,
        span.start_char,
        span.end_char,
        span.start_byte,
        span.end_byte,
        span.text,
    )


def _source_span_identity(candidate: LensCandidate) -> tuple[object, ...]:
    span = candidate.source_span
    return (
        span.doc_id,
        span.chunk_id,
        span.start_char,
        span.end_char,
        span.start_byte,
        span.end_byte,
        span.text,
    )


__all__ = [
    "build_dedup_clusters",
    "build_dedup_rejections",
    "canonical_value_key_for_candidate",
    "deduplicate_candidates",
]
