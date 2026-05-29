from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from extractor.audit import AuditStore
from extractor.config import load_config
from extractor.contracts import LLMCallLog
from extractor.reporter import (
    verify_signed_report_manifest,
    write_report,
    write_signed_report_manifest,
)
from tests.unit.test_reporter import (
    COMPLETED,
    HASH,
    make_data_point,
    make_manifest,
    make_schema_metadata,
    seed_audit_store,
)


PROMPT_HASH = "d" * 64


def make_llm_call_log() -> LLMCallLog:
    return LLMCallLog(
        call_id="call-1",
        run_id="run-1",
        stage="planner.propose_schema",
        attempt=1,
        model="test-model",
        prompt_sha256=PROMPT_HASH,
        input_tokens=10,
        output_tokens=5,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        latency_ms=100,
        stop_reason="tool_use",
        tool_name="extract_schema",
        created_at=datetime(2026, 5, 30, 11, 0, tzinfo=timezone.utc),
    )


def test_write_signed_report_manifest_binds_report_and_audit_identities(tmp_path) -> None:
    async def run_check() -> None:
        config = load_config(env={}, include_local=False)
        output_path = tmp_path / "reports" / "run-1.json"
        env = {"VERITEXT_REPORT_SIGNING_KEY": "phase-40-secret"}
        data_point = make_data_point().model_copy(update={"confidence": 0.9})

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store, make_manifest(), (data_point,))
            await audit_store.record_llm_call_log(make_llm_call_log())
            report_result = await write_report(
                manifest=make_manifest(),
                data_points=(data_point,),
                schema_metadata=make_schema_metadata(),
                output_path=output_path,
                audit_store=audit_store,
                generated_at=COMPLETED,
            )

            manifest = await write_signed_report_manifest(
                report_result=report_result,
                audit_store=audit_store,
                config=config,
                env=env,
            )

            manifest_path = output_path.with_name(f"{output_path.name}.manifest.json")
            assert manifest_path.is_file()
            assert manifest.artifact.artifact_sha256 == report_result.output_sha256
            assert manifest.artifact.byte_length == report_result.output_byte_length
            assert manifest.artifact.run_id == "run-1"
            assert manifest.source_sha256s == (HASH,)
            assert manifest.prompt_sha256s == (PROMPT_HASH,)
            assert manifest.schema_hashes == (report_result.report.schema_metadata.schema_hash,)
            assert manifest.confidence_buckets[0].item_ids == ("dp-1",)
            assert manifest.audit_chain_head_sha256 == "0" * 64
            event = (await audit_store.list_audit_integrity_events(run_id="run-1"))[0]
            assert event.previous_chain_hash == manifest.audit_chain_head_sha256
            assert verify_signed_report_manifest(
                report_path=output_path,
                manifest=manifest,
                config=config,
                env=env,
            )

            output_path.write_text('{"tampered":true}\n', encoding="utf-8")
            assert not verify_signed_report_manifest(
                report_path=output_path,
                manifest=manifest,
                config=config,
                env=env,
            )

    asyncio.run(run_check())
