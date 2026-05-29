from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from extractor.audit import AuditStore
from extractor.contracts import CategoryDefinition, DataPoint, FieldDefinition, SourceSpan
from extractor.contracts import build_planner_generated_schema_metadata
from extractor.reporter import diff_reports, verify_signed_report_manifest, write_report
from extractor.reporter import write_signed_report_manifest
from tests.unit.test_reporter import make_document, make_manifest, seed_audit_store


GENERATED = datetime(2026, 5, 30, 13, 0, tzinfo=timezone.utc)


def make_generic_data_point(
    *,
    run_id: str,
    data_point_id: str,
    field_name: str,
    value: str,
    confidence: float,
) -> DataPoint:
    return DataPoint(
        data_point_id=data_point_id,
        run_id=run_id,
        doc_id="doc-1",
        category="GenericFact",
        field_name=field_name,
        value=value,
        source_span=SourceSpan(
            doc_id="doc-1",
            chunk_id="chunk-1",
            start_char=0,
            end_char=len(value),
            start_byte=0,
            end_byte=len(value.encode("utf-8")),
            text=value,
        ),
        confidence=confidence,
        contributing_candidate_ids=(f"candidate-{data_point_id}",),
        critic_report_ids=(f"critic-{data_point_id}",),
        verifier_report_ids=(f"verifier-{data_point_id}",),
        reconciliation_decision_id=f"decision-{data_point_id}",
    )


def make_generic_schema_metadata():
    return build_planner_generated_schema_metadata(
        approved_categories=(
            CategoryDefinition(
                name="GenericFact",
                description="A source-backed generic fact.",
                fields=(
                    FieldDefinition(
                        name="shared_value",
                        description="A comparable source-backed value.",
                        value_type="text",
                        required=True,
                    ),
                ),
            ),
        ),
        domain_hints=(),
    )


def test_signed_manifest_and_diff_acceptance_are_source_neutral(tmp_path) -> None:
    async def run_check() -> None:
        from extractor.config import load_config

        config = load_config(env={}, include_local=False)
        env = {"REPORT_SIGNING_KEY": "phase-40-secret"}
        base_point = make_generic_data_point(
            run_id="run-1",
            data_point_id="dp-base",
            field_name="shared_value",
            value="value-one",
            confidence=0.91,
        )
        candidate_point = make_generic_data_point(
            run_id="run-2",
            data_point_id="dp-candidate",
            field_name="shared_value",
            value="value-two",
            confidence=0.72,
        )
        base_output = tmp_path / "base.json"
        candidate_output = tmp_path / "candidate.json"

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store, make_manifest(), (base_point,))
            base_report_result = await write_report(
                manifest=make_manifest(),
                data_points=(base_point,),
                schema_metadata=make_generic_schema_metadata(),
                output_path=base_output,
                audit_store=audit_store,
                generated_at=GENERATED,
            )
            signed_manifest = await write_signed_report_manifest(
                report_result=base_report_result,
                audit_store=audit_store,
                config=config,
                env=env,
            )

        assert verify_signed_report_manifest(
            report_path=base_output,
            manifest=signed_manifest,
            config=config,
            env=env,
        )
        assert signed_manifest.confidence_buckets[0].item_ids == ("dp-base",)
        assert signed_manifest.source_sha256s == (make_document().source_sha256,)

        candidate_report_result = await write_report(
            manifest=make_manifest(status="running").model_copy(update={"run_id": "run-2"}),
            data_points=(candidate_point,),
            schema_metadata=make_generic_schema_metadata(),
            output_path=candidate_output,
            audit_store=None,
            generated_at=GENERATED,
        )
        diff_report = diff_reports(
            base_report=base_report_result.report,
            candidate_report=candidate_report_result.report,
            diff_run_id="diff-source-neutral",
            generated_at=GENERATED,
        )

        assert diff_report.summary_counts["changed_value"] == 1
        assert diff_report.entries[0].old_refs[0].value == "value-one"
        assert diff_report.entries[0].new_refs[0].value == "value-two"

    asyncio.run(run_check())
