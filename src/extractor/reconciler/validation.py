from __future__ import annotations

from extractor.contracts import CriticReport, ExtractionPlan, LensCandidate, VerifierReport
from extractor.reconciler.errors import ReconcilerError


def validate_reconciler_inputs(
    *,
    plan: ExtractionPlan,
    candidates: tuple[LensCandidate, ...],
    critic_reports: tuple[CriticReport, ...],
    verifier_reports: tuple[VerifierReport, ...],
) -> tuple[dict[str, CriticReport], dict[str, VerifierReport]]:
    if not candidates:
        raise ReconcilerError("reconciler requires at least one verified candidate")

    candidate_ids: set[str] = set()
    for candidate in candidates:
        if candidate.run_id != plan.run_id:
            raise ReconcilerError("candidate run_id must match extraction plan run_id")
        if candidate.doc_id != plan.doc_id:
            raise ReconcilerError("candidate doc_id must match extraction plan doc_id")
        if candidate.candidate_id in candidate_ids:
            raise ReconcilerError("candidate IDs must be unique before reconciliation")
        candidate_ids.add(candidate.candidate_id)

    accepted_critic_reports = _accepted_critic_reports_by_candidate_id(plan, critic_reports)
    accepted_verifier_reports = _accepted_verifier_reports_by_candidate_id(
        plan,
        verifier_reports,
    )

    for candidate in candidates:
        critic_report = accepted_critic_reports.get(candidate.candidate_id)
        if critic_report is None:
            raise ReconcilerError(
                "candidate must have an accepted critic report before reconciliation"
            )
        if (
            critic_report.corrected_candidate is not None
            and critic_report.corrected_candidate != candidate
        ):
            raise ReconcilerError("candidate must match the accepted critic correction")
        if candidate.candidate_id not in accepted_verifier_reports:
            raise ReconcilerError(
                "candidate must have an accepted verifier report before reconciliation"
            )
    return accepted_critic_reports, accepted_verifier_reports


def _accepted_critic_reports_by_candidate_id(
    plan: ExtractionPlan,
    critic_reports: tuple[CriticReport, ...],
) -> dict[str, CriticReport]:
    accepted_reports: dict[str, CriticReport] = {}
    for report in critic_reports:
        if report.run_id != plan.run_id:
            raise ReconcilerError("critic report run_id must match extraction plan run_id")
        if not report.accepted:
            continue
        if report.candidate_id in accepted_reports:
            raise ReconcilerError(
                "reconciler requires exactly one accepted critic report per candidate"
            )
        accepted_reports[report.candidate_id] = report
    return accepted_reports


def _accepted_verifier_reports_by_candidate_id(
    plan: ExtractionPlan,
    verifier_reports: tuple[VerifierReport, ...],
) -> dict[str, VerifierReport]:
    accepted_reports: dict[str, VerifierReport] = {}
    for report in verifier_reports:
        if report.run_id != plan.run_id:
            raise ReconcilerError("verifier report run_id must match extraction plan run_id")
        if not report.accepted:
            continue
        if report.candidate_id in accepted_reports:
            raise ReconcilerError(
                "reconciler requires exactly one accepted verifier report per candidate"
            )
        accepted_reports[report.candidate_id] = report
    return accepted_reports


__all__ = ["validate_reconciler_inputs"]
