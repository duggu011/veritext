from __future__ import annotations

from extractor.contracts import (
    Chunk,
    CriticIssue,
    CriticReport,
    ExtractionPlan,
    LensCandidate,
    RejectionReason,
)
from extractor.contracts.models import RejectionReasonCode
from extractor.llm.views import short_candidate_id
from extractor.critic.checks import contradicted_rejection_reasons
from extractor.critic.corrections import (
    correction_rejection_reasons,
    materialize_correction,
    should_preserve_original_for_correction,
)
from extractor.critic.errors import CriticError
from extractor.critic.ids import stable_report_id
from extractor.critic.models import CriticVerdict


def build_report(
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
        raw_issues = (
            CriticIssue(
                code=_required_code(verdict),
                severity=_severity_for(_required_code(verdict)),
                message=verdict.evidence or _default_message(_required_code(verdict)),
            ),
        )
        issues = _filter_contradicted_reject_issues(
            plan=plan,
            chunk=chunk,
            candidate=candidate,
            issues=raw_issues,
        )
        accepted = not issues
        plausibility_score = 1.0 if accepted else 0.0
    else:
        corrected_candidate, structural_reasons = materialize_correction(
            raw=verdict.correction,
            original=candidate,
            chunk=chunk,
        )
        validation_reasons = list(structural_reasons)
        if corrected_candidate is not None:
            validation_reasons.extend(
                correction_rejection_reasons(
                    plan=plan,
                    chunk=chunk,
                    original=candidate,
                    corrected=corrected_candidate,
                )
            )
        if should_preserve_original_for_correction(
            plan=plan,
            chunk=chunk,
            original=candidate,
            corrected=corrected_candidate,
            reasons=validation_reasons,
        ):
            validation_reasons = []
            corrected_candidate = None
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
        report_id=stable_report_id(
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


def critic_rejection_reasons(report: CriticReport) -> list[RejectionReason]:
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


def _filter_contradicted_reject_issues(
    *,
    plan: ExtractionPlan,
    chunk: Chunk,
    candidate: LensCandidate,
    issues: tuple[CriticIssue, ...],
) -> tuple[CriticIssue, ...]:
    filtered: list[CriticIssue] = []
    for issue in issues:
        verdict = CriticVerdict(
            id=short_candidate_id(candidate.candidate_id),
            decision="reject",
            code=issue.code,
            evidence=issue.message,
        )
        if contradicted_rejection_reasons(
            plan=plan,
            chunk=chunk,
            candidate=candidate,
            verdict=verdict,
        ):
            continue
        filtered.append(issue)
    return tuple(filtered)


__all__ = ["build_report", "critic_rejection_reasons"]
