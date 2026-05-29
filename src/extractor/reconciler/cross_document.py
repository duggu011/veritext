from __future__ import annotations

import hashlib
from collections.abc import Mapping

from extractor.canonical_values import (
    canonical_value_key_for_data_point,
    canonical_value_key_identity,
)
from extractor.contracts import (
    ApprovedSchemaMetadata,
    CrossDocumentConflict,
    CrossDocumentFactGroup,
    CrossDocumentFactKey,
    CrossDocumentReconciliationResult,
    CrossDocumentSourceRef,
    DataPoint,
    Document,
)


DEFAULT_CROSS_DOCUMENT_POLICY_ID = "cross-document-default"
DEFAULT_CROSS_DOCUMENT_POLICY_VERSION = "2026-05-29"


class CrossDocumentReconciliationError(RuntimeError):
    """Raised when cross-document reconciliation cannot preserve audit links."""


def reconcile_cross_document_data_points(
    *,
    cross_document_run_id: str,
    data_points: tuple[DataPoint, ...],
    documents: tuple[Document, ...],
    schema_metadata_by_run_id: Mapping[str, ApprovedSchemaMetadata],
) -> CrossDocumentReconciliationResult:
    documents_by_id = _documents_by_id(documents)
    refs_by_data_point_id = _source_refs_by_data_point_id(
        data_points=data_points,
        documents_by_id=documents_by_id,
    )
    group_specs = _build_group_specs(
        data_points=data_points,
        refs_by_data_point_id=refs_by_data_point_id,
        schema_metadata_by_run_id=schema_metadata_by_run_id,
        cross_document_run_id=cross_document_run_id,
    )
    conflict_ids_by_group_id, conflicts = _build_conflicts(
        cross_document_run_id=cross_document_run_id,
        group_specs=tuple(group_specs),
    )
    groups = _materialize_groups(
        group_specs=tuple(group_specs),
        conflict_ids_by_group_id=conflict_ids_by_group_id,
    )
    return CrossDocumentReconciliationResult(
        cross_document_run_id=cross_document_run_id,
        input_run_ids=tuple(sorted({data_point.run_id for data_point in data_points})),
        input_doc_ids=tuple(sorted({data_point.doc_id for data_point in data_points})),
        groups=groups,
        conflicts=conflicts,
        skipped_inputs=(),
    )


def _documents_by_id(documents: tuple[Document, ...]) -> dict[str, Document]:
    documents_by_id: dict[str, Document] = {}
    for document in documents:
        existing = documents_by_id.get(document.doc_id)
        if existing is not None and existing != document:
            raise CrossDocumentReconciliationError(
                f"conflicting document payloads for doc_id {document.doc_id}"
            )
        documents_by_id[document.doc_id] = document
    return documents_by_id


def _source_refs_by_data_point_id(
    *,
    data_points: tuple[DataPoint, ...],
    documents_by_id: Mapping[str, Document],
) -> dict[str, CrossDocumentSourceRef]:
    refs: dict[str, CrossDocumentSourceRef] = {}
    for data_point in data_points:
        document = documents_by_id.get(data_point.doc_id)
        if document is None:
            raise CrossDocumentReconciliationError(
                f"missing document for data point doc_id {data_point.doc_id}"
            )
        refs[data_point.data_point_id] = CrossDocumentSourceRef(
            run_id=data_point.run_id,
            doc_id=data_point.doc_id,
            data_point_id=data_point.data_point_id,
            source_span=data_point.source_span,
            supporting_source_spans=data_point.supporting_source_spans,
            source_sha256=document.source_sha256,
            text_sha256=document.text_sha256,
            value=data_point.value,
            value_verbatim=data_point.value_verbatim,
            value_canonical=data_point.value_canonical,
            value_kind=data_point.value_kind,
            normalization_status=data_point.normalization_status,
            normalization_policy_id=data_point.normalization_policy_id,
            normalization_policy_version=data_point.normalization_policy_version,
            normalization_notes=data_point.normalization_notes,
        )
    return refs


def _build_group_specs(
    *,
    data_points: tuple[DataPoint, ...],
    refs_by_data_point_id: Mapping[str, CrossDocumentSourceRef],
    schema_metadata_by_run_id: Mapping[str, ApprovedSchemaMetadata],
    cross_document_run_id: str,
) -> list[dict[str, object]]:
    grouped: dict[tuple[object, ...], list[CrossDocumentSourceRef]] = {}
    keys_by_identity: dict[tuple[object, ...], CrossDocumentFactKey] = {}
    for data_point in sorted(data_points, key=_data_point_sort_key):
        schema_metadata = schema_metadata_by_run_id.get(data_point.run_id)
        if schema_metadata is None:
            raise CrossDocumentReconciliationError(
                f"missing schema metadata for run_id {data_point.run_id}"
            )
        fact_key = CrossDocumentFactKey(
            schema_id=schema_metadata.schema_id,
            schema_hash=schema_metadata.schema_hash,
            category=data_point.category,
            field_name=data_point.field_name,
            canonical_key=canonical_value_key_for_data_point(data_point),
            policy_id=DEFAULT_CROSS_DOCUMENT_POLICY_ID,
            policy_version=DEFAULT_CROSS_DOCUMENT_POLICY_VERSION,
        )
        identity = _fact_key_identity(fact_key)
        grouped.setdefault(identity, []).append(refs_by_data_point_id[data_point.data_point_id])
        keys_by_identity[identity] = fact_key

    specs: list[dict[str, object]] = []
    for identity in sorted(grouped):
        sources = tuple(sorted(grouped[identity], key=_source_ref_sort_key))
        fact_key = keys_by_identity[identity]
        specs.append(
            {
                "group_id": _stable_group_id(
                    cross_document_run_id=cross_document_run_id,
                    fact_key=fact_key,
                    sources=sources,
                ),
                "key": fact_key,
                "sources": sources,
            }
        )
    return specs


def _build_conflicts(
    *,
    cross_document_run_id: str,
    group_specs: tuple[dict[str, object], ...],
) -> tuple[dict[str, tuple[str, ...]], tuple[CrossDocumentConflict, ...]]:
    comparable_by_field: dict[tuple[object, ...], list[dict[str, object]]] = {}
    for spec in group_specs:
        key = spec["key"]
        assert isinstance(key, CrossDocumentFactKey)
        if key.canonical_key.source != "value_canonical":
            continue
        field_identity = (key.schema_id, key.schema_hash, key.category, key.field_name)
        comparable_by_field.setdefault(field_identity, []).append(spec)

    conflicts: list[CrossDocumentConflict] = []
    conflict_ids_by_group_id: dict[str, tuple[str, ...]] = {}
    for specs in comparable_by_field.values():
        canonical_identities = {
            canonical_value_key_identity(spec_key.canonical_key)
            for spec_key in (spec["key"] for spec in specs)
            if isinstance(spec_key, CrossDocumentFactKey)
        }
        if len(canonical_identities) <= 1:
            continue
        conflict = _build_conflict(
            cross_document_run_id=cross_document_run_id,
            specs=tuple(specs),
        )
        conflicts.append(conflict)
        for group_id in conflict.conflicting_group_ids:
            conflict_ids_by_group_id[group_id] = (conflict.conflict_id,)
    return conflict_ids_by_group_id, tuple(sorted(conflicts, key=lambda item: item.conflict_id))


def _build_conflict(
    *,
    cross_document_run_id: str,
    specs: tuple[dict[str, object], ...],
) -> CrossDocumentConflict:
    first_key = specs[0]["key"]
    assert isinstance(first_key, CrossDocumentFactKey)
    group_ids = tuple(sorted(str(spec["group_id"]) for spec in specs))
    doc_ids = tuple(
        sorted(
            {
                source.doc_id
                for spec in specs
                for source in spec["sources"]
                if isinstance(source, CrossDocumentSourceRef)
            }
        )
    )
    canonical_identities = tuple(
        sorted(
            canonical_value_key_identity(key.canonical_key)
            for key in (spec["key"] for spec in specs)
            if isinstance(key, CrossDocumentFactKey)
        )
    )
    return CrossDocumentConflict(
        conflict_id=_stable_conflict_id(
            cross_document_run_id=cross_document_run_id,
            category=first_key.category,
            field_name=first_key.field_name,
            group_ids=group_ids,
            canonical_identities=canonical_identities,
        ),
        category=first_key.category,
        field_name=first_key.field_name,
        conflicting_group_ids=group_ids,
        reason="same_field_distinct_canonical_values",
        doc_ids=doc_ids,
        canonical_key_identities=canonical_identities,
    )


def _materialize_groups(
    *,
    group_specs: tuple[dict[str, object], ...],
    conflict_ids_by_group_id: Mapping[str, tuple[str, ...]],
) -> tuple[CrossDocumentFactGroup, ...]:
    groups: list[CrossDocumentFactGroup] = []
    for spec in group_specs:
        group_id = str(spec["group_id"])
        key = spec["key"]
        sources = spec["sources"]
        assert isinstance(key, CrossDocumentFactKey)
        assert isinstance(sources, tuple)
        conflict_ids = conflict_ids_by_group_id.get(group_id, ())
        groups.append(
            CrossDocumentFactGroup(
                group_id=group_id,
                key=key,
                sources=sources,
                document_count=len({source.doc_id for source in sources}),
                conflict_status="unresolved" if conflict_ids else "none",
                conflict_ids=conflict_ids,
            )
        )
    return tuple(sorted(groups, key=lambda group: _fact_group_sort_key(group)))


def _fact_key_identity(key: CrossDocumentFactKey) -> tuple[object, ...]:
    return (
        key.schema_id,
        key.schema_hash,
        key.category,
        key.field_name,
        *canonical_value_key_identity(key.canonical_key),
        key.policy_id,
        key.policy_version,
    )


def _stable_group_id(
    *,
    cross_document_run_id: str,
    fact_key: CrossDocumentFactKey,
    sources: tuple[CrossDocumentSourceRef, ...],
) -> str:
    identity = "|".join(
        (
            cross_document_run_id,
            *("" if part is None else str(part) for part in _fact_key_identity(fact_key)),
            *(source.data_point_id for source in sources),
        )
    )
    return f"xdg-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


def _stable_conflict_id(
    *,
    cross_document_run_id: str,
    category: str,
    field_name: str,
    group_ids: tuple[str, ...],
    canonical_identities: tuple[tuple[object, ...], ...],
) -> str:
    key_parts = tuple(
        ":".join("" if part is None else str(part) for part in identity)
        for identity in canonical_identities
    )
    identity = "|".join((cross_document_run_id, category, field_name, *group_ids, *key_parts))
    return f"xdc-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


def _data_point_sort_key(data_point: DataPoint) -> tuple[str, str, str, str, str]:
    return (
        data_point.category,
        data_point.field_name,
        data_point.doc_id,
        data_point.run_id,
        data_point.data_point_id,
    )


def _source_ref_sort_key(source_ref: CrossDocumentSourceRef) -> tuple[str, str, str]:
    return (source_ref.doc_id, source_ref.run_id, source_ref.data_point_id)


def _fact_group_sort_key(group: CrossDocumentFactGroup) -> tuple[object, ...]:
    return (
        group.key.category,
        group.key.field_name,
        group.key.canonical_key.key,
        group.group_id,
    )


__all__ = [
    "CrossDocumentReconciliationError",
    "reconcile_cross_document_data_points",
]
