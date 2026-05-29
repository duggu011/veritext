from __future__ import annotations

from extractor.contracts import Chunk, ExtractionPlan, LensCandidate, SourceSpan
from extractor.contracts.models import LensName
from extractor.executor.ids import stable_candidate_id
from extractor.executor.models import ExtractedCandidatePayload


def build_candidate(
    *,
    plan: ExtractionPlan,
    lens: LensName,
    chunk: Chunk,
    payload: ExtractedCandidatePayload,
    start_char: int,
    source_text: str,
    candidate_index: int,
    executor_call_id: str,
) -> LensCandidate:
    end_char = start_char + len(source_text)
    start_byte, end_byte = _derive_byte_offsets(
        chunk=chunk,
        start_char=start_char,
        source_text=source_text,
    )
    source_span = SourceSpan(
        doc_id=plan.doc_id,
        chunk_id=chunk.chunk_id,
        start_char=start_char,
        end_char=end_char,
        start_byte=start_byte,
        end_byte=end_byte,
        text=source_text,
    )
    return LensCandidate(
        candidate_id=stable_candidate_id(
            plan=plan,
            lens=lens,
            chunk=chunk,
            payload=payload,
            start_char=start_char,
            source_text=source_text,
            candidate_index=candidate_index,
        ),
        run_id=plan.run_id,
        doc_id=plan.doc_id,
        chunk_id=chunk.chunk_id,
        lens=lens,
        category=payload.category,
        field_name=payload.field_name,
        value=payload.value,
        source_span=source_span,
        confidence=payload.confidence,
        executor_call_id=executor_call_id,
        **_normalization_metadata(value=payload.value, source_text=source_text),
    )


def _derive_byte_offsets(
    *,
    chunk: Chunk,
    start_char: int,
    source_text: str,
) -> tuple[int, int]:
    # Caller must have already verified the slice; out-of-range slices return
    # (chunk.start_byte, chunk.start_byte) and are caught by span validation.
    relative_start = start_char - chunk.start_char
    if relative_start < 0 or relative_start > len(chunk.text):
        return chunk.start_byte, chunk.start_byte
    prefix_bytes = len(chunk.text[:relative_start].encode("utf-8"))
    text_bytes = len(source_text.encode("utf-8"))
    return chunk.start_byte + prefix_bytes, chunk.start_byte + prefix_bytes + text_bytes


def _normalization_metadata(*, value: str, source_text: str) -> dict[str, object]:
    if value == source_text:
        return {
            "value_verbatim": source_text,
            "value_kind": "text",
            "normalization_status": "verbatim_only",
        }
    return {
        "value_verbatim": source_text,
        "value_canonical": value,
        "value_kind": "text",
        "normalization_status": "canonicalized",
        "normalization_policy_id": "source-traced-label",
        "normalization_policy_version": "1",
    }


__all__ = ["build_candidate"]
