from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib

from extractor.audit import AuditStore, CandidateRejection
from extractor.config import load_config
from extractor.contracts import (
    CategoryDefinition,
    DataPoint,
    Document,
    FieldDefinition,
    PageSpan,
    RejectionReason,
    RunManifest,
    SourceSpan,
    build_planner_generated_schema_metadata,
)
from extractor.reporter import (
    build_static_provenance_artifact,
    write_report,
    write_signed_report_manifest,
    write_static_provenance_html,
)


GENERATED = datetime(2026, 5, 30, 18, 0, tzinfo=timezone.utc)
STARTED = datetime(2026, 5, 30, 17, 50, tzinfo=timezone.utc)
SOURCE_HASH = "a" * 64
TEXT_HASH = "b" * 64


def make_generic_document() -> Document:
    text = "Measured value: 42 units."
    text_bytes = text.encode("utf-8")
    return Document(
        doc_id="doc-1",
        source_path="/tmp/generic.txt",
        format="plain_text",
        text=text,
        source_sha256=SOURCE_HASH,
        text_sha256=TEXT_HASH,
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


def make_generic_data_point(document: Document) -> DataPoint:
    value = "42 units"
    start = document.text.index(value)
    return DataPoint(
        data_point_id="dp-generic",
        run_id="run-1",
        doc_id=document.doc_id,
        category="GenericFact",
        field_name="measured_value",
        value=value,
        source_span=SourceSpan(
            doc_id=document.doc_id,
            chunk_id="chunk-1",
            start_char=start,
            end_char=start + len(value),
            start_byte=start,
            end_byte=start + len(value.encode("utf-8")),
            text=value,
        ),
        confidence=0.93,
        contributing_candidate_ids=("candidate-kept",),
        critic_report_ids=("critic-kept",),
        verifier_report_ids=("verifier-kept",),
        reconciliation_decision_id="decision-kept",
        value_kind="quantity",
    )


def make_generic_schema_metadata():
    return build_planner_generated_schema_metadata(
        approved_categories=(
            CategoryDefinition(
                name="GenericFact",
                description="A source-backed generic fact.",
                fields=(
                    FieldDefinition(
                        name="measured_value",
                        description="A source-backed measured value.",
                        value_type="quantity",
                        required=True,
                    ),
                ),
            ),
        ),
        domain_hints=(),
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


def make_rejection() -> CandidateRejection:
    return CandidateRejection(
        rejection_id="rejection-1",
        run_id="run-1",
        candidate_id="candidate-rejected",
        stage="critic",
        reasons=(RejectionReason(code="critic_rejected", message="Rejected generically."),),
        created_at=GENERATED,
    )


def test_static_provenance_acceptance_is_source_neutral(tmp_path) -> None:
    async def run_check() -> None:
        config = load_config(env={}, include_local=False)
        env = {"REPORT_SIGNING_KEY": "phase-42-secret"}
        document = make_generic_document()
        data_point = make_generic_data_point(document)
        schema_metadata = make_generic_schema_metadata()
        report_path = tmp_path / "generic.json"
        html_path = tmp_path / "generic.provenance.html"

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await audit_store.record_run_manifest(make_manifest())
            await audit_store.record_document(document)
            await audit_store.record_data_point(data_point)
            report_result = await write_report(
                manifest=make_manifest(),
                data_points=(data_point,),
                schema_metadata=schema_metadata,
                output_path=report_path,
                audit_store=audit_store,
                generated_at=GENERATED,
            )
            signed_manifest = await write_signed_report_manifest(
                report_result=report_result,
                audit_store=audit_store,
                config=config,
                env=env,
            )

        artifact = build_static_provenance_artifact(
            report=report_result.report,
            signed_manifest=signed_manifest,
            document=document,
            candidate_rejections=(make_rejection(),),
            diff_report=None,
            generated_at=GENERATED,
            context_radius=config.reporting.static_provenance_context_radius,
        )
        write_result = write_static_provenance_html(
            artifact=artifact,
            output_path=html_path,
        )
        html = html_path.read_text(encoding="utf-8")

        assert artifact.data_point_views[0].source_context.offset_status == "matched"
        assert artifact.data_point_views[0].confidence_bucket == "verified"
        assert artifact.manifest_identity.config_sha256 == signed_manifest.config_sha256
        assert artifact.rejection_summaries[0].reason_code == "critic_rejected"
        assert "GenericFact" in html
        assert "measured_value" in html
        assert "42 units" in html
        assert str(data_point.source_span.start_char) in html
        assert signed_manifest.config_sha256 in html
        assert schema_metadata.schema_hash in html
        assert "critic_rejected" in html
        assert write_result.output_sha256 == hashlib.sha256(
            html.encode("utf-8")
        ).hexdigest()

    asyncio.run(run_check())
