from __future__ import annotations

import re


def collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


def find_value_matches(text: str, value: str) -> list[tuple[int, int]]:
    exact_matches = find_exact_matches(text, value)
    if exact_matches:
        return [(start, start + len(value)) for start in exact_matches]

    stripped = value.strip()
    if stripped and stripped != value:
        stripped_matches = find_exact_matches(text, stripped)
        if stripped_matches:
            return [(start, start + len(stripped)) for start in stripped_matches]

    case_insensitive_matches = find_case_insensitive_matches(text, value)
    if case_insensitive_matches:
        return case_insensitive_matches

    return find_whitespace_normalized_matches(text, value)


def find_exact_matches(text: str, source: str) -> list[int]:
    matches: list[int] = []
    cursor = 0
    while cursor + len(source) <= len(text):
        idx = text.find(source, cursor)
        if idx < 0:
            break
        matches.append(idx)
        cursor = idx + 1
    return matches


def find_case_insensitive_matches(text: str, source: str) -> list[tuple[int, int]]:
    if source == "":
        return []
    return [
        (match.start(), match.end())
        for match in re.finditer(re.escape(source), text, flags=re.IGNORECASE)
    ]


def find_whitespace_normalized_matches(
    text: str,
    source: str,
) -> list[tuple[int, int]]:
    normalized_source = collapse_whitespace(source)
    if normalized_source == "" or not any(char.isspace() for char in source):
        return []

    normalized_text, mapping = normalize_whitespace_with_mapping(text)
    matches: list[tuple[int, int]] = []
    cursor = 0
    while cursor + len(normalized_source) <= len(normalized_text):
        idx = normalized_text.find(normalized_source, cursor)
        if idx < 0:
            break
        start = mapping[idx]
        end = mapping[idx + len(normalized_source) - 1] + 1
        matches.append((start, end))
        cursor = idx + 1
    return matches


def normalize_whitespace_with_mapping(text: str) -> tuple[str, list[int]]:
    normalized: list[str] = []
    mapping: list[int] = []
    in_whitespace = False
    for index, char in enumerate(text):
        if char.isspace():
            if normalized and not in_whitespace:
                normalized.append(" ")
                mapping.append(index)
            in_whitespace = True
            continue
        normalized.append(char)
        mapping.append(index)
        in_whitespace = False

    if normalized and normalized[-1] == " ":
        normalized.pop()
        mapping.pop()
    return "".join(normalized), mapping


def match_starts_in_markdown_heading(text: str, start: int) -> bool:
    line_start = text.rfind("\n", 0, start) + 1
    return text[line_start:start].lstrip().startswith("#")


def sentence_spans(text: str) -> tuple[tuple[int, str], ...]:
    spans: list[tuple[int, str]] = []
    start = 0
    index = 0
    while index < len(text):
        char = text[index]
        if char in ".!?" and _is_sentence_terminal(text=text, index=index):
            _append_sentence_span(spans=spans, text=text, start=start, end=index + 1)
            start = index + 1
        elif char == "\n" and index + 1 < len(text) and text[index + 1] == "\n":
            _append_sentence_span(spans=spans, text=text, start=start, end=index)
            start = index + 2
            index += 1
        index += 1
    _append_sentence_span(spans=spans, text=text, start=start, end=len(text))
    return tuple(spans)


def _append_sentence_span(
    *,
    spans: list[tuple[int, str]],
    text: str,
    start: int,
    end: int,
) -> None:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    if start >= end:
        return
    sentence = text[start:end]
    if sentence.lstrip().startswith("#") or not any(char.isalnum() for char in sentence):
        return
    spans.append((start, sentence))


def _is_sentence_terminal(*, text: str, index: int) -> bool:
    if index + 1 < len(text) and not text[index + 1].isspace():
        return False
    prefix = text[:index]
    token_start = max(prefix.rfind(" "), prefix.rfind("\n")) + 1
    token = prefix[token_start:] + "."
    if token.casefold() in {"mr.", "mrs.", "ms.", "dr.", "prof.", "sr.", "jr.", "st."}:
        return False
    if re.search(r"(?:[A-Z]\.){1,}[A-Z]\.$", token):
        return False

    next_index = index + 1
    while next_index < len(text) and text[next_index].isspace():
        next_index += 1
    return next_index >= len(text) or not text[next_index].islower()


__all__ = [
    "collapse_whitespace",
    "find_exact_matches",
    "find_value_matches",
    "match_starts_in_markdown_heading",
    "sentence_spans",
]
