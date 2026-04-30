from __future__ import annotations

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


def expand_compact_verdict_tuple(
    verdict: object,
    *,
    allow_correction: bool,
) -> object:
    """Expand `[id, decision_code, code, evidence, correction]` verdict tuples.

    Existing object-shaped verdicts pass through unchanged so tests and callers
    can validate the full audit-side contract directly.
    """
    if isinstance(verdict, BaseModel) or not isinstance(verdict, tuple):
        return verdict
    if len(verdict) != 5:
        return verdict

    short_id, decision_code, code, evidence, correction = verdict
    decision = _expand_decision_code(decision_code)
    if decision == "correct" and not allow_correction:
        raise ValueError("verifier compact verdicts cannot use decision_code 'c'")
    if correction is not None and not allow_correction:
        raise ValueError("verifier compact verdict correction slot must be null")

    expanded: dict[str, Any] = {
        "id": short_id,
        "decision": decision,
    }
    if code is not None:
        expanded["code"] = code
    if evidence is not None:
        expanded["evidence"] = evidence
    if correction is not None:
        expanded["correction"] = correction
    return expanded


def _expand_decision_code(decision_code: object) -> object:
    if not isinstance(decision_code, str):
        return decision_code
    return _DECISION_CODE_MAP.get(decision_code.casefold(), decision_code)


__all__ = ["expand_compact_verdict_tuple", "split_model_json_before_field"]
