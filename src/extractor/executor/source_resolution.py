from __future__ import annotations

from dataclasses import dataclass

from extractor.contracts import Chunk, RejectionReason
from extractor.executor.models import ExtractedCandidatePayload
from extractor.executor.text_utils import (
    collapse_whitespace,
    find_exact_matches,
    find_value_matches,
    match_starts_in_markdown_heading,
)


@dataclass(frozen=True)
class SourceTextResolution:
    start_char: int
    source_text: str
    rejection_reasons: tuple[RejectionReason, ...] = ()


_SHORT_AMBIGUOUS_SPAN_MAX_CHARS = 24
_OFFSET_REPAIR_FIELDS = frozenset({"metric_name", "period"})


def resolve_source_text(
    *,
    payload: ExtractedCandidatePayload,
    chunk: Chunk,
) -> SourceTextResolution:
    """Find the safest chunk-backed span for the model's offset/length claim.

    The normal path is a direct chunk slice from start_char + source_length. If
    that span is structurally invalid, a unique value match can repair
    offset/length typos. A valid source slice does not need to contain the value
    literally: values can be semantic labels such as "appointment" while the
    source span contains the sentence that supports that label.
    """
    text = chunk.text
    claimed = _slice_claimed_source_text(payload=payload, chunk=chunk)
    value_matches = find_value_matches(text, payload.value)

    if claimed is None:
        if len(value_matches) == 1:
            start, end = value_matches[0]
            return SourceTextResolution(
                start_char=chunk.start_char + start,
                source_text=text[start:end],
            )

        reasons = [_invalid_source_length_reason(payload=payload, chunk=chunk)]
        if len(value_matches) > 1:
            reasons.extend(
                _ambiguous_source_span_reason(payload.value, len(value_matches))
            )
        return _fallback_resolution(chunk=chunk, rejection_reasons=tuple(reasons))

    claimed_source = claimed[2]
    claimed_exact_matches = find_exact_matches(text, claimed_source)
    claimed_is_ambiguous = _is_short_ambiguous_source(
        claimed_source,
        claimed_exact_matches,
    )
    claimed_supports_value = _source_supports_value(claimed_source, payload.value)
    if len(value_matches) == 1 and not claimed_supports_value:
        start, end = value_matches[0]
        return SourceTextResolution(
            start_char=chunk.start_char + start,
            source_text=text[start:end],
        )
    if len(value_matches) > 1 and not claimed_supports_value:
        repaired_match = _select_header_adjacent_value_match(
            payload=payload,
            chunk=chunk,
            matches=value_matches,
        )
        if repaired_match is not None:
            start, end = repaired_match
            return SourceTextResolution(
                start_char=chunk.start_char + start,
                source_text=text[start:end],
            )

    rejection_reasons: tuple[RejectionReason, ...] = ()
    if claimed_is_ambiguous:
        rejection_reasons = _ambiguous_source_span_reason(
            claimed_source,
            len(claimed_exact_matches),
        )
    elif len(value_matches) > 1 and not claimed_supports_value:
        reasons = [_unsupported_value_reason(payload=payload)]
        reasons.extend(_ambiguous_source_span_reason(payload.value, len(value_matches)))
        rejection_reasons = tuple(reasons)

    return SourceTextResolution(
        start_char=payload.start_char,
        source_text=claimed_source,
        rejection_reasons=rejection_reasons,
    )


def _slice_claimed_source_text(
    *,
    payload: ExtractedCandidatePayload,
    chunk: Chunk,
) -> tuple[int, int, str] | None:
    relative_start = payload.start_char - chunk.start_char
    relative_end = relative_start + payload.source_length
    if (
        relative_start < 0
        or relative_end > len(chunk.text)
        or payload.source_length == 0
    ):
        return None
    return relative_start, relative_end, chunk.text[relative_start:relative_end]


def _select_header_adjacent_value_match(
    *,
    payload: ExtractedCandidatePayload,
    chunk: Chunk,
    matches: list[tuple[int, int]],
) -> tuple[int, int] | None:
    if payload.field_name not in _OFFSET_REPAIR_FIELDS:
        return None

    relative_claimed_start = payload.start_char - chunk.start_char
    body_matches = [
        match
        for match in matches
        if not match_starts_in_markdown_heading(chunk.text, match[0])
    ]
    if not body_matches:
        return None

    after_claim = [match for match in body_matches if match[0] >= relative_claimed_start]
    if after_claim:
        return min(after_claim, key=lambda match: match[0])
    if len(body_matches) == 1:
        return body_matches[0]
    return None


def _source_supports_value(source: str, value: str) -> bool:
    if value in source:
        return True
    stripped = value.strip()
    if stripped and stripped in source:
        return True
    return collapse_whitespace(value).casefold() in collapse_whitespace(source).casefold()


def _invalid_source_length_reason(
    *,
    payload: ExtractedCandidatePayload,
    chunk: Chunk,
) -> RejectionReason:
    return RejectionReason(
        code="invalid_source_offsets",
        message=(
            f"Candidate source_length {payload.source_length} at start_char "
            f"{payload.start_char} does not fit chunk "
            f"[{chunk.start_char}, {chunk.end_char})."
        ),
    )


def _unsupported_value_reason(
    *,
    payload: ExtractedCandidatePayload,
) -> RejectionReason:
    return RejectionReason(
        code="invalid_source_offsets",
        message=(
            "Candidate length-based source span does not contain the emitted "
            f"value {payload.value!r}."
        ),
    )


def _fallback_resolution(
    *,
    chunk: Chunk,
    rejection_reasons: tuple[RejectionReason, ...],
) -> SourceTextResolution:
    return SourceTextResolution(
        start_char=chunk.start_char,
        source_text=chunk.text[:1],
        rejection_reasons=rejection_reasons,
    )


def _is_short_ambiguous_source(source: str, matches: list[int]) -> bool:
    return len(matches) > 1 and len(source) <= _SHORT_AMBIGUOUS_SPAN_MAX_CHARS


def _ambiguous_source_span_reason(
    source: str,
    match_count: int,
) -> tuple[RejectionReason, ...]:
    return (
        RejectionReason(
            code="ambiguous_source_span",
            message=(
                f"Candidate span text {source!r} appears {match_count} times in "
                "the chunk; emit a wider unique source_length to preserve provenance."
            ),
        ),
    )


__all__ = ["SourceTextResolution", "resolve_source_text"]
