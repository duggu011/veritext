import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from extractor.audit import AuditStore
from extractor.contracts import (
    Document,
    PageSpan,
    PlanningRefusal,
    RunManifest,
    SchemaSelectionPolicy,
)
from extractor.reporter import write_refusal_report


HASH = "a" * 64
STARTED = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)
COMPLETED = STARTED + timedelta(minutes=5)


def make_document() -> Document:
    text = "Revenue increased."
    return Document(
        doc_id="doc-1",
        source_path="/tmp/doc.txt",
        format="plain_text",
        text=text,
        source_sha256=HASH,
        text_sha256="b" * 64,
        source_byte_length=len(text.encode("utf-8")),
        text_byte_length=len(text.encode("utf-8")),
        page_map=(
            PageSpan(
                page_number=1,
                start_char=0,
                end_char=len(text),
                start_byte=0,
                end_byte=len(text.encode("utf-8")),
            ),
        ),
    )


def make_manifest() -> RunManifest:
    return RunManifest(
        run_id="run-1",
        doc_id="doc-1",
        audit_db_path="/tmp/audit.sqlite3",
        status="running",
        started_at=STARTED,
        output_data_point_ids=(),
    )


def make_refusal() -> PlanningRefusal:
    return PlanningRefusal(
        run_id="run-1",
        doc_id="doc-1",
        document_class="financial_update",
        domain_hints=("finance",),
        policy=SchemaSelectionPolicy(
            require_approved_schema=True,
            minimum_schema_coverage=0.65,
            allow_planner_generated_fallback=False,
        ),
        candidate_schema_ids=(),
        fit_assessments=(),
        reason_codes=("no_approved_schema_candidates",),
    )


def test_write_refusal_report_serializes_refusal_and_marks_manifest_refused(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        output_path = tmp_path / "refusal.json"
        manifest = make_manifest()
        refusal = make_refusal()

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await audit_store.record_run_manifest(manifest)
            await audit_store.record_document(make_document())

            result = await write_refusal_report(
                manifest=manifest,
                refusal=refusal,
                output_path=output_path,
                audit_store=audit_store,
                generated_at=COMPLETED,
            )
            stored_manifest = await audit_store.get_run_manifest("run-1")

        rendered = output_path.read_text(encoding="utf-8")
        payload = json.loads(rendered)
        assert payload["report_schema_version"] == "refusal.v1"
        assert payload["outcome_type"] == "schema_fit_refusal"
        assert payload["run_id"] == "run-1"
        assert payload["doc_id"] == "doc-1"
        assert payload["refusal"]["reason_codes"] == ["no_approved_schema_candidates"]
        assert "data_points" not in payload
        assert result.output_sha256 == hashlib.sha256(rendered.encode("utf-8")).hexdigest()
        assert result.completed_manifest.status == "refused"
        assert result.completed_manifest.completed_at == COMPLETED
        assert result.completed_manifest.output_data_point_ids == ()
        assert stored_manifest == result.completed_manifest

    asyncio.run(run_check())
