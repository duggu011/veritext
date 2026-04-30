from __future__ import annotations

import hashlib

from datetime import datetime, timezone

from extractor.audit import CandidateRejection
from extractor.contracts import LensCandidate, RejectionReason


def deduplicate_candidates(
    candidates: tuple[LensCandidate, ...],
) -> tuple[tuple[LensCandidate, ...], dict[str, str]]:
    by_key: dict[tuple[str, str, str, str, str], list[LensCandidate]] = {}
    for candidate in candidates:
        key = (
            candidate.chunk_id,
            candidate.category,
            candidate.field_name,
            candidate.source_span.text,
            candidate.value,
        )
        by_key.setdefault(key, []).append(candidate)

    canonical: list[LensCandidate] = []
    merged_into: dict[str, str] = {}
    for group in by_key.values():
        primary, *duplicates = sorted(group, key=lambda item: item.candidate_id)
        canonical.append(primary)
        for duplicate in duplicates:
            merged_into[duplicate.candidate_id] = primary.candidate_id

    return tuple(canonical), merged_into


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


__all__ = ["build_dedup_rejections", "deduplicate_candidates"]
