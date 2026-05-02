from __future__ import annotations

from extractor.contracts import Chunk
from extractor.executor.field_normalizers import NORMALIZERS
from extractor.executor.models import ExtractedCandidatePayload
from extractor.executor.source_resolution import (
    SourceTextResolution,
    resolve_source_text,
)


def prepare_candidate_payload(
    *,
    payload: ExtractedCandidatePayload,
    chunk: Chunk,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution]:
    resolution = resolve_source_text(payload=payload, chunk=chunk)
    return _normalize_resolved_candidate(
        payload=payload,
        resolution=resolution,
        chunk=chunk,
    )


def _normalize_resolved_candidate(
    *,
    payload: ExtractedCandidatePayload,
    resolution: SourceTextResolution,
    chunk: Chunk,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution]:
    if resolution.rejection_reasons:
        return payload, resolution

    for normalizer in NORMALIZERS:
        normalized = normalizer(payload, resolution, chunk)
        if normalized is not None:
            payload, resolution = normalized

    return payload, resolution


__all__ = ["prepare_candidate_payload"]
