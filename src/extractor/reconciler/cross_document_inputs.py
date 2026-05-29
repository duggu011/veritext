from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from extractor.contracts import (
    ApprovedSchemaMetadata,
    CrossDocumentSkippedInput,
    DataPoint,
    Document,
    RunManifest,
)
from extractor.reconciler.errors import CrossDocumentReconciliationError


@dataclass(frozen=True)
class PreparedCrossDocumentInputs:
    data_points: tuple[DataPoint, ...]
    skipped_inputs: tuple[CrossDocumentSkippedInput, ...]
    input_run_ids: tuple[str, ...]
    input_doc_ids: tuple[str, ...]


def prepare_cross_document_inputs(
    *,
    data_points: tuple[DataPoint, ...],
    documents_by_id: Mapping[str, Document],
    schema_metadata_by_run_id: Mapping[str, ApprovedSchemaMetadata],
    run_manifests: tuple[RunManifest, ...] = (),
) -> PreparedCrossDocumentInputs:
    data_points_by_id = _data_points_by_id(data_points)
    manifests_by_run_id = _manifests_by_run_id(run_manifests)
    skipped: list[CrossDocumentSkippedInput] = []
    skipped_run_ids: set[str] = set()

    for manifest in sorted(run_manifests, key=lambda item: item.run_id):
        if manifest.status != "completed":
            skipped_run_ids.add(manifest.run_id)
            skipped.append(_skipped(manifest.run_id, "run", "run_not_completed"))
            continue
        for data_point_id in manifest.output_data_point_ids:
            if data_point_id not in data_points_by_id:
                skipped.append(_skipped(data_point_id, "data_point", "missing_data_point"))

    prepared: list[DataPoint] = []
    for data_point in sorted(data_points, key=_data_point_sort_key):
        if data_point.run_id in skipped_run_ids:
            continue
        if manifests_by_run_id and data_point.run_id not in manifests_by_run_id:
            skipped.append(_skipped(data_point.data_point_id, "data_point", "missing_run_manifest"))
            continue
        if data_point.doc_id not in documents_by_id:
            skipped.append(_skipped(data_point.data_point_id, "data_point", "missing_document"))
            continue
        if data_point.run_id not in schema_metadata_by_run_id:
            skipped.append(
                _skipped(data_point.data_point_id, "data_point", "missing_schema_metadata")
            )
            continue
        prepared.append(data_point)

    return PreparedCrossDocumentInputs(
        data_points=tuple(prepared),
        skipped_inputs=tuple(sorted(skipped, key=_skipped_input_sort_key)),
        input_run_ids=_input_run_ids(data_points=data_points, run_manifests=run_manifests),
        input_doc_ids=_input_doc_ids(data_points=data_points, run_manifests=run_manifests),
    )


def _data_points_by_id(data_points: tuple[DataPoint, ...]) -> dict[str, DataPoint]:
    data_points_by_id: dict[str, DataPoint] = {}
    for data_point in data_points:
        existing = data_points_by_id.get(data_point.data_point_id)
        if existing is not None and existing != data_point:
            raise CrossDocumentReconciliationError(
                f"duplicate data_point_id {data_point.data_point_id}"
            )
        data_points_by_id[data_point.data_point_id] = data_point
    return data_points_by_id


def _manifests_by_run_id(run_manifests: tuple[RunManifest, ...]) -> dict[str, RunManifest]:
    manifests_by_run_id: dict[str, RunManifest] = {}
    for manifest in run_manifests:
        existing = manifests_by_run_id.get(manifest.run_id)
        if existing is not None and existing != manifest:
            raise CrossDocumentReconciliationError(f"duplicate run_id {manifest.run_id}")
        manifests_by_run_id[manifest.run_id] = manifest
    return manifests_by_run_id


def _input_run_ids(
    *,
    data_points: tuple[DataPoint, ...],
    run_manifests: tuple[RunManifest, ...],
) -> tuple[str, ...]:
    if run_manifests:
        return tuple(sorted({manifest.run_id for manifest in run_manifests}))
    return tuple(sorted({data_point.run_id for data_point in data_points}))


def _input_doc_ids(
    *,
    data_points: tuple[DataPoint, ...],
    run_manifests: tuple[RunManifest, ...],
) -> tuple[str, ...]:
    if run_manifests:
        return tuple(sorted({manifest.doc_id for manifest in run_manifests}))
    return tuple(sorted({data_point.doc_id for data_point in data_points}))


def _skipped(
    input_id: str,
    input_kind: str,
    reason: str,
) -> CrossDocumentSkippedInput:
    return CrossDocumentSkippedInput(
        input_id=input_id,
        input_kind=input_kind,
        reason=reason,
    )


def _data_point_sort_key(data_point: DataPoint) -> tuple[str, str, str]:
    return (data_point.doc_id, data_point.run_id, data_point.data_point_id)


def _skipped_input_sort_key(item: CrossDocumentSkippedInput) -> tuple[str, str, str]:
    return (item.input_kind, item.input_id, item.reason)


__all__ = ["PreparedCrossDocumentInputs", "prepare_cross_document_inputs"]
