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
_QUALIFIER_PHRASES = (
    ("approximately",),
    ("approx",),
    ("about",),
    ("around",),
    ("at", "least"),
    ("at", "most"),
    ("no", "more", "than"),
    ("no", "less", "than"),
    ("more", "than"),
    ("less", "than"),
    ("up",),
    ("down",),
)
_SCOPED_METRIC_TOKENS = frozenset(
    {
        "annual",
        "fy",
        "full",
        "full-year",
        "fullyear",
        "q1",
        "q2",
        "q3",
        "q4",
        "quarter",
        "quarterly",
        "year",
        "year-end",
        "yearend",
    }
)
_GENERIC_METRIC_ROLE_TOKENS = frozenset({"guidance", "metric", "measure"})


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


def candidate_source_specificity_rank(
    candidate: LensCandidate,
) -> tuple[int, int, int, int, int, int, str]:
    """Rank source candidates for deterministic reconciliation tie-breaking."""
    unsupported = 0 if value_is_source_supported(candidate) else 1
    if is_label_field(candidate.field_name):
        field_rank = (
            _label_extra_source_token_count(candidate),
            _label_value_shape(candidate),
            0,
        )
    elif _is_percentage_or_exposure_field(candidate.field_name):
        field_rank = (
            _percentage_qualifier_rank(candidate),
            0,
            0,
        )
    elif _is_name_field(candidate.field_name):
        field_rank = _name_field_rank(candidate)
    else:
        field_rank = (
            0 if _same_normalized(candidate.value, candidate.source_span.text) else 1,
            0,
            0,
        )
    return (
        unsupported,
        *field_rank,
        len(candidate.source_span.text),
        len(candidate.value),
        candidate.candidate_id,
    )


def is_label_field(field_name: str) -> bool:
    return field_name in _LABEL_FIELDS or field_name.endswith("_type")


def _label_value_shape(candidate: LensCandidate) -> int:
    if not source_traced_label_value(candidate):
        return 2
    if _same_normalized(candidate.value, candidate.source_span.text):
        return 1
    return 0


def _label_extra_source_token_count(candidate: LensCandidate) -> int:
    value_tokens = {_canonical_token(token) for token in _tokens(candidate.value)}
    source_tokens = tuple(
        _canonical_token(token) for token in _tokens(candidate.source_span.text)
    )
    if not value_tokens:
        return len(source_tokens)
    return sum(1 for token in source_tokens if token not in value_tokens)


def _percentage_qualifier_rank(candidate: LensCandidate) -> int:
    source_tokens = _tokens(candidate.source_span.text)
    value_tokens = _tokens(candidate.value)
    source_has_qualifier = _has_qualifier_phrase(source_tokens)
    value_has_qualifier = _has_qualifier_phrase(value_tokens)
    if source_has_qualifier and value_has_qualifier:
        return 0
    if source_has_qualifier:
        return 2
    return 1


def _name_field_rank(candidate: LensCandidate) -> tuple[int, int, int]:
    if candidate.category != "ForwardGuidance" or candidate.field_name != "metric_name":
        return (
            0 if _same_normalized(candidate.value, candidate.source_span.text) else 1,
            0,
            0,
        )

    tokens = set(_tokens(f"{candidate.value} {candidate.source_span.text}"))
    scope_rank = 0 if _has_scoped_metric_token(tokens) else 1
    generic_role_rank = 1 if tokens & _GENERIC_METRIC_ROLE_TOKENS else 0
    return (scope_rank, generic_role_rank, -len(_tokens(candidate.value)))


def _is_percentage_or_exposure_field(field_name: str) -> bool:
    return (
        field_name.endswith("_pct")
        or field_name.endswith("_percentage")
        or field_name.endswith("_rate")
        or "exposure" in field_name
    )


def _is_name_field(field_name: str) -> bool:
    return field_name == "metric_name" or field_name.endswith("_name")


def _has_qualifier_phrase(tokens: tuple[str, ...]) -> bool:
    return any(_contains_phrase(tokens, phrase) for phrase in _QUALIFIER_PHRASES)


def _has_scoped_metric_token(tokens: set[str]) -> bool:
    if tokens & _SCOPED_METRIC_TOKENS:
        return True
    return any(token.isdigit() and len(token) == 4 for token in tokens)


def _contains_phrase(tokens: tuple[str, ...], phrase: tuple[str, ...]) -> bool:
    if len(phrase) > len(tokens):
        return False
    return any(
        tokens[index : index + len(phrase)] == phrase
        for index in range(len(tokens) - len(phrase) + 1)
    )


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
