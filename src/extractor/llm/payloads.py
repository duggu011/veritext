from __future__ import annotations

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


__all__ = ["split_model_json_before_field"]
