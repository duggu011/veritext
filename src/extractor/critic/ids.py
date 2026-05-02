from __future__ import annotations

import hashlib

from extractor.contracts import CriticIssue, CriticReport, LensCandidate, RejectionReason


def stable_report_id(
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


def stable_mirrored_report_id(
    *,
    primary_report: CriticReport,
    duplicate: LensCandidate,
) -> str:
    identity = f"{primary_report.report_id}|{duplicate.candidate_id}|mirrored"
    return f"critic-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


def stable_rejection_id(
    candidate: LensCandidate,
    report: CriticReport,
    reasons: list[RejectionReason],
) -> str:
    reason_identity = "|".join(f"{reason.code}:{reason.message}" for reason in reasons)
    identity = f"{candidate.candidate_id}|{report.report_id}|{reason_identity}"
    return f"rejection-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


def stable_missing_rejection_id(
    *,
    candidate: LensCandidate,
    critic_call_id: str,
    reasons: list[RejectionReason],
) -> str:
    reason_identity = "|".join(f"{reason.code}:{reason.message}" for reason in reasons)
    identity = f"{candidate.candidate_id}|{critic_call_id}|missing|{reason_identity}"
    return f"rejection-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


__all__ = [
    "stable_missing_rejection_id",
    "stable_mirrored_report_id",
    "stable_rejection_id",
    "stable_report_id",
]
