from __future__ import annotations

import hashlib

from extractor.contracts import Chunk, ExtractionPlan, LensCandidate, RejectionReason
from extractor.contracts.models import LensName
from extractor.executor.models import ExtractedCandidatePayload


def stable_candidate_id(
    *,
    plan: ExtractionPlan,
    lens: LensName,
    chunk: Chunk,
    payload: ExtractedCandidatePayload,
    start_char: int,
    source_text: str,
    candidate_index: int,
) -> str:
    identity = "|".join(
        (
            plan.run_id,
            plan.doc_id,
            chunk.chunk_id,
            lens,
            str(candidate_index),
            payload.category,
            payload.field_name,
            payload.value,
            str(start_char),
            source_text,
        )
    )
    return f"candidate-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


def stable_rejection_id(
    candidate: LensCandidate,
    reasons: list[RejectionReason],
) -> str:
    reason_identity = "|".join(f"{reason.code}:{reason.message}" for reason in reasons)
    identity = f"{candidate.candidate_id}|{reason_identity}"
    return f"rejection-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


__all__ = ["stable_candidate_id", "stable_rejection_id"]
