from __future__ import annotations

from extractor.contracts import Chunk, CriticReport, ExtractionPlan, LensCandidate
from extractor.verifier.errors import VerifierError


def validate_verifier_inputs(
    *,
    plan: ExtractionPlan,
    chunks: tuple[Chunk, ...],
    candidates: tuple[LensCandidate, ...],
    critic_reports: tuple[CriticReport, ...],
) -> tuple[dict[str, Chunk], dict[str, CriticReport]]:
    if not chunks:
        raise VerifierError("verifier requires chunks for candidate context")

    chunks_by_id: dict[str, Chunk] = {}
    for chunk in chunks:
        if chunk.doc_id != plan.doc_id:
            raise VerifierError("chunk doc_id must match extraction plan doc_id")
        chunks_by_id[chunk.chunk_id] = chunk

    accepted_reports: dict[str, CriticReport] = {}
    for report in critic_reports:
        if report.run_id != plan.run_id:
            raise VerifierError("critic report run_id must match extraction plan run_id")
        if not report.accepted:
            continue
        if report.candidate_id in accepted_reports:
            raise VerifierError(
                "verifier requires exactly one accepted critic report per candidate"
            )
        accepted_reports[report.candidate_id] = report

    for candidate in candidates:
        if candidate.run_id != plan.run_id:
            raise VerifierError("candidate run_id must match extraction plan run_id")
        if candidate.doc_id != plan.doc_id:
            raise VerifierError("candidate doc_id must match extraction plan doc_id")
        if candidate.chunk_id not in chunks_by_id:
            raise VerifierError("candidate chunk_id must reference a provided chunk")

        report = accepted_reports.get(candidate.candidate_id)
        if report is None:
            raise VerifierError(
                "candidate must have an accepted critic report before verification"
            )
        if report.corrected_candidate is not None and report.corrected_candidate != candidate:
            raise VerifierError("candidate must match the accepted critic correction")
    return chunks_by_id, accepted_reports


__all__ = ["validate_verifier_inputs"]
