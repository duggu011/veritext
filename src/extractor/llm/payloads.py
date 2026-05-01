from __future__ import annotations

import json

from typing import Any

from pydantic import BaseModel


def split_model_json_before_field(
    payload: BaseModel,
    field_name: str,
) -> tuple[str, str]:
    """Split a Pydantic JSON object before one field's value for prompt caching.

    The two returned strings concatenate back to the exact original JSON. The
    stable prefix can therefore carry Anthropic cache_control without changing
    what the model sees when cache support is disabled or unavailable.
    """
    rendered = payload.model_dump_json()
    marker = f'"{field_name}":'
    marker_index = rendered.find(marker)
    if marker_index < 0:
        raise ValueError(f"Field {field_name!r} was not found in payload JSON")
    value_index = marker_index + len(marker)
    return rendered[:value_index], rendered[value_index:]


_DECISION_CODE_MAP = {
    "a": "accept",
    "accept": "accept",
    "r": "reject",
    "reject": "reject",
    "c": "correct",
    "correct": "correct",
}


def normalize_verdict_payload(
    verdict: object,
    *,
    allow_correction: bool,
    evidence_max_chars: int | None = None,
    default_reject_code: str | None = None,
) -> object:
    """Normalize compact and full verdict payloads before model validation.

    Compact `[id, decision_code, code, evidence, correction]` arrays are the LLM
    wire shape. Evidence is optional; if the model exceeds the cap, omit it so
    the verdict code still reaches deterministic service handling.
    """
    verdict = parse_json_if_string(verdict)
    if isinstance(verdict, BaseModel):
        return verdict
    if isinstance(verdict, dict):
        sanitized = _drop_overlong_evidence(verdict, evidence_max_chars=evidence_max_chars)
        sanitized = _expand_dict_decision_code(sanitized)
        sanitized = _default_dict_reject_code(
            sanitized,
            default_reject_code=default_reject_code,
        )
        if allow_correction:
            sanitized = _drop_contradictory_correction(sanitized)
        return sanitized
    if not isinstance(verdict, (list, tuple)):
        return verdict
    verdict = _trim_trailing_null_slots(verdict)
    if len(verdict) < 2 or len(verdict) > 5:
        return verdict
    verdict = (*verdict, *((None,) * (5 - len(verdict))))

    short_id, decision_code, code, evidence, correction = verdict
    decision = _expand_decision_code(decision_code)
    if decision == "correct" and not allow_correction:
        raise ValueError("verifier compact verdicts cannot use decision_code 'c'")
    if decision == "reject" and code is None and default_reject_code is not None:
        code = default_reject_code
    if correction is not None and not allow_correction:
        raise ValueError("verifier compact verdict correction slot must be null")

    expanded: dict[str, Any] = {
        "id": short_id,
        "decision": decision,
    }
    if code is not None:
        expanded["code"] = code
    if _valid_evidence(evidence, evidence_max_chars=evidence_max_chars):
        expanded["evidence"] = evidence
    if correction is not None:
        expanded["correction"] = correction
    return expanded


def parse_json_if_string(value: object) -> object:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _expand_decision_code(decision_code: object) -> object:
    if not isinstance(decision_code, str):
        return decision_code
    return _DECISION_CODE_MAP.get(decision_code.casefold(), decision_code)


def _expand_dict_decision_code(verdict: dict[str, object]) -> dict[str, object]:
    decision = verdict.get("decision")
    expanded = _expand_decision_code(decision)
    if expanded == decision:
        return verdict
    sanitized = dict(verdict)
    sanitized["decision"] = expanded
    return sanitized


def _default_dict_reject_code(
    verdict: dict[str, object],
    *,
    default_reject_code: str | None,
) -> dict[str, object]:
    if (
        verdict.get("decision") != "reject"
        or verdict.get("code") is not None
        or default_reject_code is None
    ):
        return verdict
    sanitized = dict(verdict)
    sanitized["code"] = default_reject_code
    return sanitized


def _trim_trailing_null_slots(verdict: list[object] | tuple[object, ...]) -> tuple[object, ...]:
    trimmed = tuple(verdict)
    while len(trimmed) > 5 and trimmed[-1] is None:
        trimmed = trimmed[:-1]
    return trimmed


def _drop_overlong_evidence(
    verdict: dict[str, object],
    *,
    evidence_max_chars: int | None,
) -> dict[str, object]:
    evidence = verdict.get("evidence")
    if _valid_evidence(evidence, evidence_max_chars=evidence_max_chars):
        return verdict
    sanitized = dict(verdict)
    sanitized.pop("evidence", None)
    return sanitized


def _drop_contradictory_correction(verdict: dict[str, object]) -> dict[str, object]:
    # A correction payload is meaningful only on `decision="correct"`. Models
    # occasionally hedge by attaching a correction to an accept/reject verdict;
    # the strict CriticVerdict validator would otherwise abort the whole batch.
    # Drop the contradictory correction so the verdict's primary decision still
    # reaches deterministic critic handling.
    correction = verdict.get("correction")
    if correction is None:
        return verdict
    decision = verdict.get("decision")
    if decision == "correct":
        return verdict
    sanitized = dict(verdict)
    sanitized.pop("correction", None)
    return sanitized


def _valid_evidence(evidence: object, *, evidence_max_chars: int | None) -> bool:
    if evidence is None:
        return False
    if evidence_max_chars is None or not isinstance(evidence, str):
        return True
    return len(evidence) <= evidence_max_chars


__all__ = [
    "normalize_verdict_payload",
    "parse_json_if_string",
    "split_model_json_before_field",
]
