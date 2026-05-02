from __future__ import annotations

from extractor.contracts import Chunk, ExtractionPlan, LensCandidate
from extractor.critic.checks import approved_category_fields, span_matches_chunk
from extractor.critic.errors import CriticError


def validate_critic_inputs(
    plan: ExtractionPlan,
    chunks: tuple[Chunk, ...],
    candidates: tuple[LensCandidate, ...],
) -> dict[str, Chunk]:
    if not chunks:
        raise CriticError("critic requires chunks for candidate context")

    chunks_by_id: dict[str, Chunk] = {}
    for chunk in chunks:
        if chunk.doc_id != plan.doc_id:
            raise CriticError("chunk doc_id must match extraction plan doc_id")
        chunks_by_id[chunk.chunk_id] = chunk

    category_fields = approved_category_fields(plan)
    for candidate in candidates:
        if candidate.run_id != plan.run_id:
            raise CriticError("candidate run_id must match extraction plan run_id")
        if candidate.doc_id != plan.doc_id:
            raise CriticError("candidate doc_id must match extraction plan doc_id")
        chunk = chunks_by_id.get(candidate.chunk_id)
        if chunk is None:
            raise CriticError("candidate chunk_id must reference a provided chunk")
        fields = category_fields.get(candidate.category)
        if fields is None or candidate.field_name not in fields:
            raise CriticError(
                "critic candidates must already satisfy the approved schema"
            )
        if not span_matches_chunk(candidate.source_span, chunk):
            raise CriticError(
                "critic candidates must preserve source spans that match chunk text"
            )
    return chunks_by_id


__all__ = ["validate_critic_inputs"]
