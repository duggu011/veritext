import asyncio
import hashlib
import importlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from extractor.audit import AuditStore
from extractor.contracts import (
    CategoryDefinition,
    CrossDocumentRunManifest,
    DataPoint,
    Document,
    FieldDefinition,
    PageSpan,
    RunManifest,
    SourceSpan,
    build_planner_generated_schema_metadata,
)
from extractor.reporter import ReporterError, write_report
from tests.unit.test_phase_39_cross_document_audit import make_cross_document_result


HASH = "a" * 64
STARTED = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)
COMPLETED = STARTED + timedelta(minutes=5)


def make_document() -> Document:
    text = "Revenue increased. Margin declined."
    text_bytes = text.encode("utf-8")
    return Document(
        doc_id="doc-1",
        source_path="/tmp/doc.txt",
        format="plain_text",
        text=text,
        source_sha256=HASH,
        text_sha256="b" * 64,
        source_byte_length=len(text_bytes),
        text_byte_length=len(text_bytes),
        page_map=(
            PageSpan(
                page_number=1,
                start_char=0,
                end_char=len(text),
                start_byte=0,
                end_byte=len(text_bytes),
            ),
        ),
    )


def make_manifest(status: str = "running") -> RunManifest:
    return RunManifest(
        run_id="run-1",
        doc_id="doc-1",
        audit_db_path="/tmp/audit.sqlite3",
        status=status,
        started_at=STARTED,
        output_data_point_ids=(),
    )


def make_data_point(
    *,
    data_point_id: str = "dp-1",
    value: str = "Revenue increased",
    start_char: int = 0,
) -> DataPoint:
    return DataPoint(
        data_point_id=data_point_id,
        run_id="run-1",
        doc_id="doc-1",
        category="Finding",
        field_name="summary",
        value=value,
        source_span=SourceSpan(
            doc_id="doc-1",
            chunk_id="chunk-1",
            start_char=start_char,
            end_char=start_char + len(value),
            start_byte=start_char,
            end_byte=start_char + len(value.encode("utf-8")),
            text=value,
        ),
        confidence=0.8,
        contributing_candidate_ids=(f"candidate-{data_point_id}",),
        critic_report_ids=(f"critic-{data_point_id}",),
        verifier_report_ids=(f"verifier-{data_point_id}",),
        reconciliation_decision_id=f"decision-{data_point_id}",
    )


def make_schema_metadata():
    category = CategoryDefinition(
        name="Finding",
        description="A source-backed finding.",
        fields=(
            FieldDefinition(
                name="summary",
                description="Short source-backed summary.",
                value_type="text",
                required=True,
            ),
        ),
    )
    return build_planner_generated_schema_metadata(
        approved_categories=(category,),
        domain_hints=("generic",),
    )


def _write_cross_document_report():
    reporter = importlib.import_module("extractor.reporter")
    value = getattr(reporter, "write_cross_document_report", None)
    assert value is not None, "write_cross_document_report must be exported"
    return value


def make_cross_document_manifest() -> CrossDocumentRunManifest:
    result = make_cross_document_result()
    return CrossDocumentRunManifest(
        cross_document_run_id=result.cross_document_run_id,
        audit_db_path="/tmp/audit.sqlite3",
        status="running",
        started_at=STARTED,
        completed_at=None,
        input_run_ids=result.input_run_ids,
        output_group_ids=(),
        output_conflict_ids=(),
    )


async def seed_audit_store(
    audit_store: AuditStore,
    manifest: RunManifest,
    data_points: tuple[DataPoint, ...],
) -> None:
    await audit_store.record_run_manifest(manifest)
    await audit_store.record_document(make_document())
    for data_point in data_points:
        await audit_store.record_data_point(data_point)


def test_write_report_serializes_output_and_completes_manifest(tmp_path: Path) -> None:
    async def run_check() -> None:
        manifest = make_manifest()
        first = make_data_point(data_point_id="dp-1", value="Revenue increased", start_char=0)
        second = make_data_point(data_point_id="dp-2", value="Margin declined", start_char=19)
        output_path = tmp_path / "reports" / "run-1.json"

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store, manifest, (first, second))
            result = await write_report(
                manifest=manifest,
                data_points=(second, first),
                schema_metadata=make_schema_metadata(),
                output_path=output_path,
                audit_store=audit_store,
                generated_at=COMPLETED,
            )
            stored_manifest = await audit_store.get_run_manifest("run-1")

        rendered = output_path.read_text(encoding="utf-8")
        payload = json.loads(rendered)

        assert result.output_path == str(output_path)
        assert result.output_sha256 == hashlib.sha256(rendered.encode("utf-8")).hexdigest()
        assert result.output_byte_length == len(rendered.encode("utf-8"))
        assert payload["report_schema_version"] == "report.v2"
        assert payload["run_id"] == "run-1"
        assert payload["schema_metadata"]["schema_id"].startswith("schema:")
        assert payload["schema_metadata"]["source_kind"] == "planner_generated"
        assert payload["output_data_point_ids"] == ["dp-1", "dp-2"]
        assert [item["data_point_id"] for item in payload["data_points"]] == ["dp-1", "dp-2"]
        assert stored_manifest == result.completed_manifest
        assert stored_manifest.status == "completed"
        assert stored_manifest.completed_at == COMPLETED
        assert stored_manifest.output_data_point_ids == ("dp-1", "dp-2")

    asyncio.run(run_check())


def test_write_cross_document_report_serializes_output_and_completes_manifest(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        write_cross_document_report = _write_cross_document_report()
        manifest = make_cross_document_manifest()
        result = make_cross_document_result()
        output_path = tmp_path / "reports" / "xrun-1.json"

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await audit_store.record_cross_document_run_manifest(manifest)
            await audit_store.record_cross_document_reconciliation_result(result)
            write_result = await write_cross_document_report(
                manifest=manifest,
                result=result,
                output_path=output_path,
                audit_store=audit_store,
                generated_at=COMPLETED,
            )
            stored_manifest = await audit_store.get_cross_document_run_manifest("xrun-1")

        rendered = output_path.read_text(encoding="utf-8")
        payload = json.loads(rendered)

        assert write_result.output_sha256 == hashlib.sha256(
            rendered.encode("utf-8")
        ).hexdigest()
        assert payload["report_schema_version"] == "cross_document_report.v1"
        assert payload["cross_document_run_id"] == "xrun-1"
        assert payload["input_run_ids"] == ["run-a", "run-b"]
        assert payload["output_group_ids"] == [result.groups[0].group_id]
        assert payload["groups"][0]["sources"][0]["data_point_id"] == "dp-a"
        assert payload["conflicts"] == []
        assert payload["skipped_inputs"] == []
        assert stored_manifest == write_result.completed_manifest
        assert stored_manifest.status == "completed"
        assert stored_manifest.completed_at == COMPLETED
        assert stored_manifest.output_group_ids == (result.groups[0].group_id,)

    asyncio.run(run_check())


def test_write_report_serializes_phase_38_additive_data_point_fields(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        manifest = make_manifest()
        source_span = SourceSpan(
            doc_id="doc-1",
            chunk_id="chunk-2",
            start_char=19,
            end_char=34,
            start_byte=19,
            end_byte=34,
            text="Margin declined",
        )
        data_point = make_data_point().model_copy(
            update={
                "supporting_source_spans": (source_span,),
                "conflict_status": "unresolved",
                "conflict_group_id": "conflict-1",
                "conflict_reason": "same_field_distinct_canonical_values",
            }
        )
        output_path = tmp_path / "reports" / "run-1.json"

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store, manifest, (data_point,))
            await write_report(
                manifest=manifest,
                data_points=(data_point,),
                schema_metadata=make_schema_metadata(),
                output_path=output_path,
                audit_store=audit_store,
                generated_at=COMPLETED,
            )

        payload = json.loads(output_path.read_text(encoding="utf-8"))
        serialized_point = payload["data_points"][0]
        assert payload["report_schema_version"] == "report.v2"
        assert serialized_point["supporting_source_spans"][0]["text"] == "Margin declined"
        assert serialized_point["conflict_status"] == "unresolved"
        assert serialized_point["conflict_group_id"] == "conflict-1"
        assert (
            serialized_point["conflict_reason"]
            == "same_field_distinct_canonical_values"
        )

    asyncio.run(run_check())


def test_write_report_rejects_missing_audited_data_point_without_output(tmp_path: Path) -> None:
    async def run_check() -> None:
        manifest = make_manifest()
        data_point = make_data_point()
        output_path = tmp_path / "run-1.json"

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await audit_store.record_run_manifest(manifest)
            await audit_store.record_document(make_document())

            with pytest.raises(ReporterError, match="missing from audit store"):
                await write_report(
                    manifest=manifest,
                    data_points=(data_point,),
                    schema_metadata=make_schema_metadata(),
                    output_path=output_path,
                    audit_store=audit_store,
                    generated_at=COMPLETED,
                )
            stored_manifest = await audit_store.get_run_manifest("run-1")

        assert not output_path.exists()
        assert stored_manifest == manifest

    asyncio.run(run_check())


def test_write_report_rejects_data_point_manifest_mismatch(tmp_path: Path) -> None:
    async def run_check() -> None:
        bad_data_point = make_data_point().model_copy(update={"run_id": "run-2"})

        with pytest.raises(ReporterError, match="data point run_id must match"):
            await write_report(
                manifest=make_manifest(),
                data_points=(bad_data_point,),
                schema_metadata=make_schema_metadata(),
                output_path=tmp_path / "run-1.json",
                generated_at=COMPLETED,
            )

        assert not (tmp_path / "run-1.json").exists()

    asyncio.run(run_check())


def test_write_report_rejects_failed_manifest(tmp_path: Path) -> None:
    async def run_check() -> None:
        with pytest.raises(ReporterError, match="failed runs cannot be completed"):
            await write_report(
                manifest=make_manifest(status="failed"),
                data_points=(make_data_point(),),
                schema_metadata=make_schema_metadata(),
                output_path=tmp_path / "run-1.json",
                generated_at=COMPLETED,
            )

        assert not (tmp_path / "run-1.json").exists()

    asyncio.run(run_check())
