from __future__ import annotations

import re

from extractor.contracts import LensCandidate


_TOKEN_RE = re.compile(r"[a-z0-9]+")
_LABEL_FIELDS = frozenset(
    {
        "event_type",
        "change_type",
        "risk_type",
        "exposure_type",
        "action_type",
        "status_type",
    }
)


def value_is_source_supported(candidate: LensCandidate) -> bool:
    """Return whether a candidate value is grounded in its selected source span."""
    value = _collapse_whitespace(candidate.value)
    source = _collapse_whitespace(candidate.source_span.text)
    if value.casefold() in source.casefold():
        return True
    if source_traced_label_value(candidate):
        return True

    source_tokens = {_canonical_token(token) for token in _tokens(source)}
    value_tokens = tuple(_canonical_token(token) for token in _tokens(value))
    return bool(value_tokens) and all(token in source_tokens for token in value_tokens)


def source_traced_label_value(candidate: LensCandidate) -> bool:
    if not is_label_field(candidate.field_name):
        return False

    value = _collapse_whitespace(candidate.value).casefold()
    source = _collapse_whitespace(candidate.source_span.text).casefold()
    if value and value in source:
        return True

    source_tokens = {_canonical_token(token) for token in _tokens(source)}
    value_tokens = tuple(_canonical_token(token) for token in _tokens(value))
    if value_tokens and all(token in source_tokens for token in value_tokens):
        return True

    return False


def correction_expands_source_span(
    *,
    original: LensCandidate,
    corrected: LensCandidate,
) -> bool:
    original_span = original.source_span
    corrected_span = corrected.source_span
    return (
        corrected_span.start_char < original_span.start_char
        or corrected_span.end_char > original_span.end_char
        or corrected_span.start_byte < original_span.start_byte
        or corrected_span.end_byte > original_span.end_byte
    )


def candidate_source_specificity_rank(candidate: LensCandidate) -> tuple[int, int, int, int, str]:
    """Rank source candidates for deterministic reconciliation tie-breaking."""
    unsupported = 0 if value_is_source_supported(candidate) else 1
    if is_label_field(candidate.field_name):
        value_shape = 0 if source_traced_label_value(candidate) else 1
    else:
        value_shape = 0 if _same_normalized(candidate.value, candidate.source_span.text) else 1
    return (
        unsupported,
        value_shape,
        len(candidate.source_span.text),
        len(candidate.value),
        candidate.candidate_id,
    )


def is_label_field(field_name: str) -> bool:
    return field_name in _LABEL_FIELDS or field_name.endswith("_type")


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(_TOKEN_RE.findall(text.casefold()))


def _canonical_token(token: str) -> str:
    if token.startswith("approv"):
        return "approv"
    if token.startswith(("acquir", "acquis")):
        return "acquis"
    if token.startswith("commenc"):
        return "commenc"
    if token.startswith(("operat", "operation")):
        return "operat"
    if token.startswith("appoint"):
        return "appoint"
    if token.startswith("retir"):
        return "retir"
    if token in {"began", "begin", "begun", "start", "started", "starts"}:
        return "commenc"
    for suffix in ("ments", "ment", "ingly", "ing", "edly", "ed", "es", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _same_normalized(left: str, right: str) -> bool:
    return _collapse_whitespace(left).casefold() == _collapse_whitespace(right).casefold()


def _collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


__all__ = [
    "candidate_source_specificity_rank",
    "correction_expands_source_span",
    "is_label_field",
    "source_traced_label_value",
    "value_is_source_supported",
]
