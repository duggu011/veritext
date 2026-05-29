from __future__ import annotations

import hashlib

from extractor.canonical_values import (
    canonical_value_key_for_data_point,
    canonical_value_key_identity,
)
from extractor.contracts import DataPoint


def mark_unresolved_conflicts(data_points: tuple[DataPoint, ...]) -> tuple[DataPoint, ...]:
    conflicts_by_field: dict[tuple[str, str, str], list[DataPoint]] = {}
    for data_point in data_points:
        key = (data_point.doc_id, data_point.category, data_point.field_name)
        conflicts_by_field.setdefault(key, []).append(data_point)

    conflict_updates: dict[str, tuple[str, str]] = {}
    for group in conflicts_by_field.values():
        comparable_group = tuple(
            data_point
            for data_point in group
            if data_point.normalization_status == "canonicalized"
        )
        canonical_keys = {
            canonical_value_key_identity(canonical_value_key_for_data_point(data_point))
            for data_point in comparable_group
        }
        if len(canonical_keys) <= 1:
            continue

        conflict_group_id = _stable_conflict_group_id(group=comparable_group)
        for data_point in comparable_group:
            conflict_updates[data_point.data_point_id] = (
                conflict_group_id,
                "same_field_distinct_canonical_values",
            )

    if not conflict_updates:
        return data_points

    marked: list[DataPoint] = []
    for data_point in data_points:
        update = conflict_updates.get(data_point.data_point_id)
        if update is None:
            marked.append(data_point)
            continue

        conflict_group_id, conflict_reason = update
        marked.append(
            data_point.model_copy(
                update={
                    "conflict_status": "unresolved",
                    "conflict_group_id": conflict_group_id,
                    "conflict_reason": conflict_reason,
                }
            )
        )
    return tuple(marked)


def _stable_conflict_group_id(*, group: tuple[DataPoint, ...]) -> str:
    first = group[0]
    key_parts = sorted(
        ":".join(
            "" if part is None else str(part)
            for part in canonical_value_key_identity(key)
        )
        for key in (canonical_value_key_for_data_point(data_point) for data_point in group)
    )
    identity = "|".join(
        (
            first.run_id,
            first.doc_id,
            first.category,
            first.field_name,
            *key_parts,
        )
    )
    return f"conflict-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


__all__ = ["mark_unresolved_conflicts"]
