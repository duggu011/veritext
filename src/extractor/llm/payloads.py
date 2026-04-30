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


def normalize_verdict_payload(
    verdict: object,
    *,
    allow_correction: bool,
    evidence_max_chars: int | None = None,
) -> object:
    """Normalize compact and full verdict payloads before model validation.

    Compact `[id, decision_code, code, evidence, correction]` arrays are the LLM
    wire shape. Evidence is optional; if the model exceeds the cap, omit it so
    the verdict code still reaches deterministic service handling.
    """
    if isinstance(verdict, BaseModel):
        return verdict
    if isinstance(verdict, dict):
        return _drop_overlong_evidence(verdict, evidence_max_chars=evidence_max_chars)
    if not isinstance(verdict, (list, tuple)) or len(verdict) != 5:
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
    if _valid_evidence(evidence, evidence_max_chars=evidence_max_chars):
        expanded["evidence"] = evidence
    if correction is not None:
        expanded["correction"] = correction
    return expanded


def _expand_decision_code(decision_code: object) -> object:
    if not isinstance(decision_code, str):
        return decision_code
    return _DECISION_CODE_MAP.get(decision_code.casefold(), decision_code)


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


def _valid_evidence(evidence: object, *, evidence_max_chars: int | None) -> bool:
    if evidence is None:
        return False
    if evidence_max_chars is None or not isinstance(evidence, str):
        return True
    return len(evidence) <= evidence_max_chars


__all__ = ["normalize_verdict_payload", "split_model_json_before_field"]
