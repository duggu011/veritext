from __future__ import annotations

import re

from extractor.contracts import Chunk
from extractor.contracts.models import LensName
from extractor.executor.models import ExtractedCandidatePayload
from extractor.executor.text_utils import collapse_whitespace, sentence_spans


_DERIVED_EVENT_CONFIDENCE = 0.82
_COMMENCEMENT_EVENT_RE = re.compile(
    r"\b(?:commenced|began|started)\s+(?:commercial\s+)?operations?\b",
    re.IGNORECASE,
)
_ACQUISITION_APPROVAL_EVENT_RE = re.compile(
    r"\bapproved\s+(?:acquiring|(?:the\s+)?acquisition(?:\s+of)?)",
    re.IGNORECASE,
)


def expand_candidate_payloads(
    *,
    payloads: tuple[ExtractedCandidatePayload, ...],
    lens: LensName,
    chunk: Chunk,
    category_fields: dict[str, frozenset[str]],
) -> tuple[ExtractedCandidatePayload, ...]:
    expanded = list(payloads)
    seen = {_candidate_payload_key(payload) for payload in payloads}
    if lens == "event":
        for payload in _derive_event_payloads(
            chunk=chunk,
            category_fields=category_fields,
        ):
            key = _candidate_payload_key(payload)
            if key in seen:
                continue
            seen.add(key)
            expanded.append(payload)
    return tuple(expanded)


def _derive_event_payloads(
    *,
    chunk: Chunk,
    category_fields: dict[str, frozenset[str]],
) -> tuple[ExtractedCandidatePayload, ...]:
    event_categories = tuple(
        category
        for category, fields in category_fields.items()
        if "event_type" in fields
    )
    if not event_categories:
        return ()

    payloads: list[ExtractedCandidatePayload] = []
    for sentence_start, sentence_text in sentence_spans(chunk.text):
        commencement = _COMMENCEMENT_EVENT_RE.search(sentence_text)
        acquisition_approval = _ACQUISITION_APPROVAL_EVENT_RE.search(sentence_text)
        if commencement is None and acquisition_approval is None:
            continue

        for category in event_categories:
            fields = category_fields[category]
            if commencement is not None:
                payloads.append(
                    _candidate_payload_from_local_span(
                        category=category,
                        field_name="event_type",
                        value="Facility commencement",
                        chunk=chunk,
                        local_start=sentence_start + commencement.start(),
                        source_text=commencement.group(0),
                    )
                )
                if "summary" in fields:
                    payloads.append(
                        _candidate_payload_from_local_span(
                            category=category,
                            field_name="summary",
                            value=sentence_text,
                            chunk=chunk,
                            local_start=sentence_start,
                            source_text=sentence_text,
                        )
                    )
                if "asset_detail" in fields:
                    payloads.append(
                        _candidate_payload_from_local_span(
                            category=category,
                            field_name="asset_detail",
                            value=sentence_text,
                            chunk=chunk,
                            local_start=sentence_start,
                            source_text=sentence_text,
                        )
                    )

            if acquisition_approval is not None:
                payloads.append(
                    _candidate_payload_from_local_span(
                        category=category,
                        field_name="event_type",
                        value="Acquisition approval",
                        chunk=chunk,
                        local_start=sentence_start + acquisition_approval.start(),
                        source_text=acquisition_approval.group(0),
                    )
                )
                if "summary" in fields:
                    payloads.append(
                        _candidate_payload_from_local_span(
                            category=category,
                            field_name="summary",
                            value=sentence_text,
                            chunk=chunk,
                            local_start=sentence_start,
                            source_text=sentence_text,
                        )
                    )

    return tuple(payloads)


def _candidate_payload_from_local_span(
    *,
    category: str,
    field_name: str,
    value: str,
    chunk: Chunk,
    local_start: int,
    source_text: str,
) -> ExtractedCandidatePayload:
    return ExtractedCandidatePayload(
        category=category,
        field_name=field_name,
        value=value,
        start_char=chunk.start_char + local_start,
        source_length=len(source_text),
        confidence=_DERIVED_EVENT_CONFIDENCE,
    )


def _candidate_payload_key(
    payload: ExtractedCandidatePayload,
) -> tuple[str, str, str, int, int]:
    return (
        payload.category,
        payload.field_name,
        collapse_whitespace(payload.value).casefold(),
        payload.start_char,
        payload.source_length,
    )


__all__ = ["expand_candidate_payloads"]
