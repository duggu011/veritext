from __future__ import annotations

import re
from collections.abc import Callable

from extractor.contracts import Chunk
from extractor.executor.models import ExtractedCandidatePayload
from extractor.executor.source_resolution import SourceTextResolution
from extractor.executor.text_utils import collapse_whitespace, find_value_matches


Normalizer = Callable[
    [ExtractedCandidatePayload, SourceTextResolution, Chunk],
    tuple[ExtractedCandidatePayload, SourceTextResolution] | None,
]

_PRIOR_PERIOD_VALUE_RE = re.compile(
    r"(?:[$€£]\s*)?\d[\d,]*(?:\.\d+)?"
    r"(?:\s+(?:million|billion|thousand))?"
    r"\s+in\s+Q[1-4]\s+\d{4}",
    re.IGNORECASE,
)
_LEADING_NUMERIC_RE = re.compile(r"(?:[$€£]\s*)?\d[\d,]*(?:\.\d+)?")
_ROLE_LABEL_BY_ATOMIC_FIELD = {
    "forecast_value": "forecast",
    "margin": "margin",
    "target_value": "target",
}
_ROLE_LABELED_ATOMIC_RE = re.compile(
    r"^(?P<value>"
    r"(?:approximately|about|at\s+least|at\s+most|no\s+more\s+than|up\s+to|"
    r"over|under|more\s+than|less\s+than)?\s*"
    r"(?:[$€£]\s*)?"
    r"\d[\d,]*(?:\.\d+)?"
    r"(?:\s*(?:%|percent|basis\s+points|bps))?"
    r"(?:\s+(?:million|billion|thousand|gigawatt-hours|megawatt-hours|"
    r"gigawatts|megawatts|hours|days|months|years))?"
    r"(?:\s+(?:to|-)\s+(?:[$€£]\s*)?\d[\d,]*(?:\.\d+)?"
    r"(?:\s*(?:%|percent))?"
    r"(?:\s+(?:million|billion|thousand|gigawatt-hours|megawatt-hours|"
    r"gigawatts|megawatts|hours|days|months|years))?)?"
    r")\s+(?P<label>forecast|margin|target)\b",
    re.IGNORECASE,
)
_EFFECTIVE_DATE_EVENT_CONTEXT_RE = re.compile(
    r"^(?P<context>\s+(?:Annual|Special|Extraordinary|General|Shareholder|"
    r"Shareholders'?|Stockholder|Stockholders'?|Board)\s+Meeting\b)",
    re.IGNORECASE,
)
_SPEAKER_ROLE_PREFIX_RE = re.compile(
    r"^(?:CEO|CFO|COO|CTO|CIO|CMO|Chair|Chairman|Chairwoman|President|Director|"
    r"Chief Executive Officer)\s+",
    re.IGNORECASE,
)


def normalize_label_value(
    payload: ExtractedCandidatePayload,
    resolution: SourceTextResolution,
    chunk: Chunk,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution] | None:
    del chunk
    if payload.field_name not in {"event_type", "change_type"}:
        return None

    source_key = collapse_whitespace(resolution.source_text).casefold()
    value_key = collapse_whitespace(payload.value).casefold()
    key = f"{source_key} {value_key}"

    if "commenced operation" in key and payload.field_name == "event_type":
        return _normalize_to_source_phrase(
            payload=payload,
            resolution=resolution,
            phrase="commenced operation",
            value="Facility commencement",
        )
    if "approved acquiring" in key and payload.field_name == "event_type":
        return _normalize_to_source_phrase(
            payload=payload,
            resolution=resolution,
            phrase="approved acquiring",
            value="Acquisition approval",
        )
    if "appointed" in key and payload.field_name == "change_type":
        return _normalize_to_source_phrase(
            payload=payload,
            resolution=resolution,
            phrase="appointed",
            value="appointment",
        )
    return None


def normalize_prior_period_value(
    payload: ExtractedCandidatePayload,
    resolution: SourceTextResolution,
    chunk: Chunk,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution] | None:
    if payload.field_name != "prior_period_value":
        return None

    numeric_key = _leading_numeric_key(payload.value) or _leading_numeric_key(
        resolution.source_text
    )
    if numeric_key is None:
        return None

    current_relative_start = resolution.start_char - chunk.start_char
    matches = [
        match
        for match in _PRIOR_PERIOD_VALUE_RE.finditer(chunk.text)
        if _numeric_keys_match(numeric_key, match.group(0))
    ]
    if not matches:
        return None

    selected = min(matches, key=lambda match: abs(match.start() - current_relative_start))
    source_text = selected.group(0)
    return (
        payload.model_copy(update={"value": source_text}),
        SourceTextResolution(
            start_char=chunk.start_char + selected.start(),
            source_text=source_text,
            rejection_reasons=resolution.rejection_reasons,
        ),
    )


def normalize_condition_value(
    payload: ExtractedCandidatePayload,
    resolution: SourceTextResolution,
    chunk: Chunk,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution] | None:
    if payload.field_name != "condition":
        return None

    start_char = resolution.start_char
    source_text = resolution.source_text
    if source_text.casefold().startswith("with "):
        start_char += len("with ")
        source_text = source_text[len("with ") :]

    source_text = _extend_condition_clause(
        chunk=chunk,
        start_char=start_char,
        source_text=source_text,
    )
    if start_char == resolution.start_char and source_text == resolution.source_text:
        return None

    return (
        payload.model_copy(update={"value": source_text}),
        SourceTextResolution(
            start_char=start_char,
            source_text=source_text,
            rejection_reasons=resolution.rejection_reasons,
        ),
    )


def normalize_effective_date_event_context(
    payload: ExtractedCandidatePayload,
    resolution: SourceTextResolution,
    chunk: Chunk,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution] | None:
    if payload.field_name != "effective_date":
        return None

    relative_end = resolution.start_char - chunk.start_char + len(resolution.source_text)
    if relative_end < 0 or relative_end > len(chunk.text):
        return None
    match = _EFFECTIVE_DATE_EVENT_CONTEXT_RE.match(chunk.text[relative_end:])
    if match is None:
        return None

    source_text = resolution.source_text + match.group("context")
    return (
        payload.model_copy(update={"value": source_text}),
        SourceTextResolution(
            start_char=resolution.start_char,
            source_text=source_text,
            rejection_reasons=resolution.rejection_reasons,
        ),
    )


def normalize_role_labeled_atomic_value(
    payload: ExtractedCandidatePayload,
    resolution: SourceTextResolution,
    chunk: Chunk,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution] | None:
    del chunk
    expected_label = _ROLE_LABEL_BY_ATOMIC_FIELD.get(payload.field_name)
    if expected_label is None:
        return None

    leading_ws = len(resolution.source_text) - len(resolution.source_text.lstrip())
    stripped_source = resolution.source_text.lstrip()
    match = _ROLE_LABELED_ATOMIC_RE.match(stripped_source)
    if match is None or match.group("label").casefold() != expected_label:
        return None

    value = match.group("value").strip()
    if value == "":
        return None
    value_start = leading_ws + match.start("value")
    return (
        payload.model_copy(update={"value": value}),
        SourceTextResolution(
            start_char=resolution.start_char + value_start,
            source_text=value,
            rejection_reasons=resolution.rejection_reasons,
        ),
    )


def normalize_notable_qualifier_value(
    payload: ExtractedCandidatePayload,
    resolution: SourceTextResolution,
    chunk: Chunk,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution] | None:
    del chunk
    if payload.field_name != "notable_qualifier":
        return None

    matches = find_value_matches(resolution.source_text, payload.value)
    if len(matches) != 1:
        return None
    start, end = matches[0]
    source_text = resolution.source_text[start:end]
    if source_text == resolution.source_text:
        return None
    return (
        payload.model_copy(update={"value": source_text}),
        SourceTextResolution(
            start_char=resolution.start_char + start,
            source_text=source_text,
            rejection_reasons=resolution.rejection_reasons,
        ),
    )


def normalize_asset_detail_operational_profile(
    payload: ExtractedCandidatePayload,
    resolution: SourceTextResolution,
    chunk: Chunk,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution] | None:
    del chunk
    if payload.field_name != "asset_detail":
        return None

    leading_ws = len(resolution.source_text) - len(resolution.source_text.lstrip())
    stripped_source = resolution.source_text.strip()
    verb_match = re.search(
        r"\b(?:operates|operated|owns|owned|includes|comprises)\s+",
        stripped_source,
        flags=re.IGNORECASE,
    )
    if verb_match is None:
        return None

    detail_start = verb_match.end()
    detail_end = len(stripped_source)
    if stripped_source.endswith("."):
        detail_end -= 1
    detail = stripped_source[detail_start:detail_end].strip()
    if not detail or not any(char.isdigit() for char in detail):
        return None

    trimmed_prefix = len(stripped_source[detail_start:detail_end]) - len(
        stripped_source[detail_start:detail_end].lstrip()
    )
    detail_start += trimmed_prefix
    return (
        payload.model_copy(update={"value": detail}),
        SourceTextResolution(
            start_char=resolution.start_char + leading_ws + detail_start,
            source_text=detail,
            rejection_reasons=resolution.rejection_reasons,
        ),
    )


def normalize_speaker_value(
    payload: ExtractedCandidatePayload,
    resolution: SourceTextResolution,
    chunk: Chunk,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution] | None:
    del chunk
    if payload.field_name != "speaker":
        return None

    match = _SPEAKER_ROLE_PREFIX_RE.match(resolution.source_text)
    if match is None:
        return None
    source_text = resolution.source_text[match.end() :]
    if len(source_text.split()) < 2:
        return None
    return (
        payload.model_copy(update={"value": source_text}),
        SourceTextResolution(
            start_char=resolution.start_char + match.end(),
            source_text=source_text,
            rejection_reasons=resolution.rejection_reasons,
        ),
    )


def _normalize_to_source_phrase(
    *,
    payload: ExtractedCandidatePayload,
    resolution: SourceTextResolution,
    phrase: str,
    value: str,
) -> tuple[ExtractedCandidatePayload, SourceTextResolution] | None:
    phrase_start = resolution.source_text.casefold().find(phrase.casefold())
    if phrase_start < 0:
        return None
    source_text = resolution.source_text[phrase_start : phrase_start + len(phrase)]
    return (
        payload.model_copy(update={"value": value}),
        SourceTextResolution(
            start_char=resolution.start_char + phrase_start,
            source_text=source_text,
            rejection_reasons=resolution.rejection_reasons,
        ),
    )


def _leading_numeric_key(text: str) -> str | None:
    match = _LEADING_NUMERIC_RE.search(text)
    if match is None:
        return None
    return collapse_whitespace(match.group(0)).casefold()


def _numeric_keys_match(expected: str, source: str) -> bool:
    actual = _leading_numeric_key(source)
    return actual == expected if actual is not None else False


def _extend_condition_clause(
    *,
    chunk: Chunk,
    start_char: int,
    source_text: str,
) -> str:
    relative_end = start_char - chunk.start_char + len(source_text)
    following = chunk.text[relative_end:]
    if not following.startswith(" under "):
        return source_text
    clause_end = len(following)
    for delimiter in (".", ";", "\n"):
        delimiter_index = following.find(delimiter)
        if delimiter_index >= 0:
            clause_end = min(clause_end, delimiter_index)
    return source_text + following[:clause_end]


NORMALIZERS: tuple[Normalizer, ...] = (
    normalize_label_value,
    normalize_prior_period_value,
    normalize_effective_date_event_context,
    normalize_role_labeled_atomic_value,
    normalize_condition_value,
    normalize_notable_qualifier_value,
    normalize_asset_detail_operational_profile,
    normalize_speaker_value,
)


__all__ = ["NORMALIZERS"]
