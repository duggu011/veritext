from __future__ import annotations

from extractor.audit import AuditStore
from extractor.contracts import CriticReport, ExtractionPlan, LensCandidate
from extractor.critic.errors import CriticError
from extractor.critic.ids import stable_mirrored_report_id


async def mirror_merged_critic_reports(
    *,
    plan: ExtractionPlan,
    reports: tuple[CriticReport, ...],
    merged_into: dict[str, str],
    merged_candidates: tuple[LensCandidate, ...],
    audit_store: AuditStore | None,
) -> tuple[tuple[LensCandidate, ...], tuple[LensCandidate, ...], tuple[CriticReport, ...]]:
    if not merged_into:
        return (), (), ()

    reports_by_candidate = {report.candidate_id: report for report in reports}
    merged_candidates_by_id = {
        candidate.candidate_id: candidate for candidate in merged_candidates
    }
    accepted: list[LensCandidate] = []
    rejected: list[LensCandidate] = []
    mirrored_reports: list[CriticReport] = []

    for duplicate_id, primary_id in sorted(merged_into.items()):
        duplicate = merged_candidates_by_id.get(duplicate_id)
        if duplicate is None:
            raise CriticError(f"merged duplicate candidate is missing: {duplicate_id}")
        if duplicate.run_id != plan.run_id or duplicate.doc_id != plan.doc_id:
            raise CriticError(
                "merged duplicate candidate must match extraction plan identity"
            )

        primary_report = reports_by_candidate.get(primary_id)
        if primary_report is None:
            continue

        mirrored_report = _mirror_critic_report(
            primary_report=primary_report,
            duplicate=duplicate,
        )
        mirrored_reports.append(mirrored_report)
        if audit_store is not None:
            await audit_store.record_critic_report(mirrored_report)

        if mirrored_report.accepted:
            accepted.append(mirrored_report.corrected_candidate or duplicate)
        else:
            rejected.append(duplicate)

    return tuple(accepted), tuple(rejected), tuple(mirrored_reports)


def _mirror_critic_report(
    *,
    primary_report: CriticReport,
    duplicate: LensCandidate,
) -> CriticReport:
    corrected_candidate = _mirror_corrected_candidate(
        corrected=primary_report.corrected_candidate,
        duplicate=duplicate,
    )
    return CriticReport(
        report_id=stable_mirrored_report_id(
            primary_report=primary_report,
            duplicate=duplicate,
        ),
        run_id=duplicate.run_id,
        candidate_id=duplicate.candidate_id,
        critic_call_id=primary_report.critic_call_id,
        plausibility_score=primary_report.plausibility_score,
        accepted=primary_report.accepted,
        issues=primary_report.issues,
        corrected_candidate=corrected_candidate,
    )


def _mirror_corrected_candidate(
    *,
    corrected: LensCandidate | None,
    duplicate: LensCandidate,
) -> LensCandidate | None:
    if corrected is None:
        return None
    return duplicate.model_copy(
        update={
            "category": corrected.category,
            "field_name": corrected.field_name,
            "value": corrected.value,
            "source_span": corrected.source_span.model_copy(
                update={
                    "doc_id": duplicate.doc_id,
                    "chunk_id": duplicate.chunk_id,
                }
            ),
            "confidence": corrected.confidence,
        }
    )


__all__ = ["mirror_merged_critic_reports"]
