from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from extractor.audit import CandidateRejection
from extractor.contracts import (
    CriticReport,
    DataPoint,
    ExtractionPlan,
    LensCandidate,
    RejectionReason,
    VerifierReport,
)
from extractor.contracts.models import RejectionReasonCode
from extractor.reconciler.errors import ReconcilerError
from extractor.reconciler.models import (
    ReconciledDataPointPayload,
    ReconciledGroupPayload,
    ReconciliationBatch,
)
from extractor.source_support import candidate_source_specificity_rank


def build_reconciliation_result(
    *,
    plan: ExtractionPlan,
    candidates_by_id: dict[str, LensCandidate],
    critic_reports_by_candidate_id: dict[str, CriticReport],
    verifier_reports_by_candidate_id: dict[str, VerifierReport],
    batch: ReconciliationBatch,
) -> tuple[tuple[DataPoint, ...], tuple[CandidateRejection, ...]]:
    _validate_output_candidate_ids(batch, candidates_by_id)

    # The model sometimes lists merged duplicates in both groups and rejected.
    # A candidate that contributes to a kept data point is not rejected — the
    # rejection loop below skips candidates already accounted as contributors.
    data_points: list[DataPoint] = []
    rejections_by_candidate_id: dict[str, CandidateRejection] = {}
    accounted_ids: set[str] = set()

    for group in batch.groups:
        payload = _payload_from_group(group=group, candidates_by_id=candidates_by_id)
        reasons = _data_point_rejection_reasons(
            plan=plan,
            payload=payload,
            candidates_by_id=candidates_by_id,
            accounted_ids=accounted_ids,
        )
        if reasons:
            for candidate_id in payload.contributing_candidate_ids:
                rejections_by_candidate_id.setdefault(
                    candidate_id,
                    _build_rejection(
                        run_id=plan.run_id,
                        candidate_id=candidate_id,
                        reasons=reasons,
                    ),
                )
                accounted_ids.add(candidate_id)
            continue

        data_point = _build_data_point(
            plan=plan,
            payload=payload,
            candidates_by_id=candidates_by_id,
            critic_reports_by_candidate_id=critic_reports_by_candidate_id,
            verifier_reports_by_candidate_id=verifier_reports_by_candidate_id,
        )
        data_points.append(data_point)
        accounted_ids.update(payload.contributing_candidate_ids)

    for candidate_id, code in batch.rejected:
        if candidate_id in accounted_ids:
            continue
        rejections_by_candidate_id[candidate_id] = _build_rejection(
            run_id=plan.run_id,
            candidate_id=candidate_id,
            reasons=(_rejection_reason_for_code(code),),
        )
        accounted_ids.add(candidate_id)

    for candidate_id in candidates_by_id:
        if candidate_id not in accounted_ids:
            rejections_by_candidate_id[candidate_id] = _build_rejection(
                run_id=plan.run_id,
                candidate_id=candidate_id,
                reasons=(
                    RejectionReason(
                        code="reconciler_rejected",
                        message=(
                            "Candidate was not selected or explicitly rejected by "
                            "reconciliation output."
                        ),
                    ),
                ),
            )

    return tuple(data_points), tuple(
        rejections_by_candidate_id[candidate_id]
        for candidate_id in sorted(rejections_by_candidate_id)
    )


def _validate_output_candidate_ids(
    batch: ReconciliationBatch,
    candidates_by_id: dict[str, LensCandidate],
) -> None:
    known_ids = set(candidates_by_id)
    for source_candidate_id, contributing_candidate_ids in batch.groups:
        unknown_ids = set(contributing_candidate_ids) - known_ids
        if source_candidate_id not in known_ids:
            unknown_ids.add(source_candidate_id)
        if unknown_ids:
            raise ReconcilerError(
                "reconciler output referenced unknown candidate IDs: "
                + ", ".join(sorted(unknown_ids))
            )

    unknown_rejection_ids = {
        candidate_id
        for candidate_id, _ in batch.rejected
        if candidate_id not in known_ids
    }
    if unknown_rejection_ids:
        raise ReconcilerError(
            "reconciler output rejected unknown candidate IDs: "
            + ", ".join(sorted(unknown_rejection_ids))
        )


def _payload_from_group(
    *,
    group: ReconciledGroupPayload,
    candidates_by_id: dict[str, LensCandidate],
) -> ReconciledDataPointPayload:
    source_candidate_id, contributing_candidate_ids = group
    source_candidate_id = _best_source_candidate_id(
        selected_source_candidate_id=source_candidate_id,
        contributing_candidate_ids=contributing_candidate_ids,
        candidates_by_id=candidates_by_id,
    )
    source_candidate = candidates_by_id[source_candidate_id]
    return ReconciledDataPointPayload(
        category=source_candidate.category,
        field_name=source_candidate.field_name,
        value=source_candidate.value,
        source_candidate_id=source_candidate_id,
        contributing_candidate_ids=contributing_candidate_ids,
        confidence=source_candidate.confidence,
    )


def _best_source_candidate_id(
    *,
    selected_source_candidate_id: str,
    contributing_candidate_ids: tuple[str, ...],
    candidates_by_id: dict[str, LensCandidate],
) -> str:
    selected = candidates_by_id[selected_source_candidate_id]
    comparable = [
        candidates_by_id[candidate_id]
        for candidate_id in contributing_candidate_ids
        if (
            candidates_by_id[candidate_id].category == selected.category
            and candidates_by_id[candidate_id].field_name == selected.field_name
        )
    ]
    if not comparable:
        return selected_source_candidate_id
    return min(comparable, key=candidate_source_specificity_rank).candidate_id


def _data_point_rejection_reasons(
    *,
    plan: ExtractionPlan,
    payload: ReconciledDataPointPayload,
    candidates_by_id: dict[str, LensCandidate],
    accounted_ids: set[str],
) -> tuple[RejectionReason, ...]:
    reasons: list[RejectionReason] = []
    fields = _approved_category_fields(plan).get(payload.category)
    if fields is None:
        reasons.append(
            RejectionReason(
                code="category_not_approved",
                message=f"Category is not approved for this extraction plan: {payload.category}",
            )
        )
    elif payload.field_name not in fields:
        reasons.append(
            RejectionReason(
                code="schema_violation",
                message=(
                    f"Field {payload.field_name} is not approved for category "
                    f"{payload.category}"
                ),
            )
        )

    for candidate_id in payload.contributing_candidate_ids:
        candidate = candidates_by_id[candidate_id]
        if candidate_id in accounted_ids:
            reasons.append(
                RejectionReason(
                    code="reconciler_rejected",
                    message=f"Candidate is assigned to more than one data point: {candidate_id}",
                )
            )
        if candidate.category != payload.category or candidate.field_name != payload.field_name:
            reasons.append(
                RejectionReason(
                    code="schema_violation",
                    message=(
                        f"Contributing candidate {candidate_id} does not match reconciled "
                        "category and field."
                    ),
                )
            )
    return _merged_rejection_reasons(tuple(reasons))


def _build_data_point(
    *,
    plan: ExtractionPlan,
    payload: ReconciledDataPointPayload,
    candidates_by_id: dict[str, LensCandidate],
    critic_reports_by_candidate_id: dict[str, CriticReport],
    verifier_reports_by_candidate_id: dict[str, VerifierReport],
) -> DataPoint:
    source_candidate = candidates_by_id[payload.source_candidate_id]
    contributing_candidate_ids = tuple(payload.contributing_candidate_ids)
    critic_report_ids = tuple(
        critic_reports_by_candidate_id[candidate_id].report_id
        for candidate_id in contributing_candidate_ids
    )
    verifier_report_ids = tuple(
        verifier_reports_by_candidate_id[candidate_id].report_id
        for candidate_id in contributing_candidate_ids
    )
    confidence = min(
        payload.confidence,
        *(candidates_by_id[candidate_id].confidence for candidate_id in contributing_candidate_ids),
        *(
            verifier_reports_by_candidate_id[candidate_id].alignment_score
            for candidate_id in contributing_candidate_ids
        ),
    )
    decision_id = _stable_decision_id(plan=plan, payload=payload)
    return DataPoint(
        data_point_id=_stable_data_point_id(
            run_id=plan.run_id,
            doc_id=plan.doc_id,
            decision_id=decision_id,
            source_candidate=source_candidate,
            value=payload.value,
        ),
        run_id=plan.run_id,
        doc_id=plan.doc_id,
        category=payload.category,
        field_name=payload.field_name,
        value=payload.value,
        source_span=source_candidate.source_span,
        confidence=confidence,
        contributing_candidate_ids=contributing_candidate_ids,
        critic_report_ids=critic_report_ids,
        verifier_report_ids=verifier_report_ids,
        reconciliation_decision_id=decision_id,
        value_verbatim=source_candidate.value_verbatim,
        value_canonical=source_candidate.value_canonical,
        value_kind=source_candidate.value_kind,
        normalization_status=source_candidate.normalization_status,
        normalization_policy_id=source_candidate.normalization_policy_id,
        normalization_policy_version=source_candidate.normalization_policy_version,
        normalization_notes=source_candidate.normalization_notes,
    )


def _build_rejection(
    *,
    run_id: str,
    candidate_id: str,
    reasons: tuple[RejectionReason, ...],
) -> CandidateRejection:
    return CandidateRejection(
        rejection_id=_stable_rejection_id(candidate_id, reasons),
        run_id=run_id,
        candidate_id=candidate_id,
        stage="reconciler",
        reasons=reasons,
        created_at=datetime.now(timezone.utc),
    )


def _rejection_reason_for_code(code: RejectionReasonCode) -> RejectionReason:
    return RejectionReason(
        code=code,
        message=_default_rejection_message(code),
    )


def _default_rejection_message(code: RejectionReasonCode) -> str:
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


def _approved_category_fields(plan: ExtractionPlan) -> dict[str, frozenset[str]]:
    return {
        category.name: frozenset(field.name for field in category.fields)
        for category in plan.approved_categories
    }


def _merged_rejection_reasons(
    reasons: tuple[RejectionReason, ...],
) -> tuple[RejectionReason, ...]:
    merged: list[RejectionReason] = []
    seen: set[tuple[str, str]] = set()
    for reason in reasons:
        key = (reason.code, reason.message)
        if key not in seen:
            merged.append(reason)
            seen.add(key)
    return tuple(merged)


def _stable_decision_id(
    *,
    plan: ExtractionPlan,
    payload: ReconciledDataPointPayload,
) -> str:
    identity = "|".join(
        (
            plan.run_id,
            plan.doc_id,
            payload.category,
            payload.field_name,
            payload.value,
            payload.source_candidate_id,
            ",".join(payload.contributing_candidate_ids),
        )
    )
    return f"reconcile-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


def _stable_data_point_id(
    *,
    run_id: str,
    doc_id: str,
    decision_id: str,
    source_candidate: LensCandidate,
    value: str,
) -> str:
    source_span = source_candidate.source_span
    identity = "|".join(
        (
            run_id,
            doc_id,
            decision_id,
            source_candidate.candidate_id,
            value,
            str(source_span.start_char),
            str(source_span.end_char),
            source_span.text,
        )
    )
    return f"datapoint-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


def _stable_rejection_id(
    candidate_id: str,
    reasons: tuple[RejectionReason, ...],
) -> str:
    reason_identity = "|".join(f"{reason.code}:{reason.message}" for reason in reasons)
    identity = f"{candidate_id}|reconciler|{reason_identity}"
    return f"rejection-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


__all__ = ["build_reconciliation_result"]
