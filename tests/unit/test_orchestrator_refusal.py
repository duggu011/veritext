import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from extractor.audit import AuditStore
from extractor.config import (
    AuditConfig,
    ChunkingConfig,
    DomainPacksConfig,
    ExecutionConfig,
    ExtractorConfig,
    LLMConfig,
    LoggingConfig,
    PromptConfig,
    SchemaRegistryConfig,
)
from extractor.contracts import LLMCallLog
from extractor.llm import StructuredLLMResult
from extractor.orchestrator import OrchestratorError, run_extraction_pipeline


ROOT = Path(__file__).resolve().parents[2]


class RefusalLLMClient:
    def __init__(self) -> None:
        self.calls: list[object] = []

    async def complete_structured(
        self,
        request: object,
        *,
        output_model: type[object],
        audit_store: AuditStore | None = None,
    ) -> StructuredLLMResult[object]:
        self.calls.append(request)
        call_log = LLMCallLog(
            call_id=f"llm-{len(self.calls)}",
            run_id=request.run_id,
            stage=request.stage,
            attempt=1,
            model="deterministic-test-model",
            prompt_sha256=request.prompt.sha256,
            input_tokens=10,
            output_tokens=5,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            latency_ms=0,
            stop_reason="tool_use",
            tool_name=request.tool_name,
            created_at=datetime.now(timezone.utc),
        )
        if audit_store is not None:
            await audit_store.record_llm_call_log(call_log)
        payload = {
            "document_type": "financial_update",
            "summary": "Revenue increased.",
            "domain_hints": ("finance",),
            "confidence": 0.9,
        }
        return StructuredLLMResult(
            output=output_model.model_validate(payload),
            call_log=call_log,
        )


def make_strict_config(tmp_path: Path) -> ExtractorConfig:
    return ExtractorConfig(
        llm=LLMConfig(
            provider="anthropic",
            model="unused-test-model",
            max_retries=0,
            timeout_seconds=30,
            max_output_tokens=512,
            temperature=0.0,
        ),
        chunking=ChunkingConfig(tokenizer="cl100k_base", window_tokens=100, overlap_tokens=0),
        execution=ExecutionConfig(
            max_stage_concurrency=1,
            max_chunk_concurrency=1,
            max_llm_attempts=1,
        ),
        audit=AuditConfig(database_path=tmp_path / "audit.sqlite3"),
        logging=LoggingConfig(level="INFO", format="json"),
        prompts=PromptConfig(directory=ROOT / "prompts"),
        domain_packs=DomainPacksConfig(directory=tmp_path / "domain_packs"),
        schema_registry=SchemaRegistryConfig(
            directory=tmp_path / "schema_registry",
            require_approved_schema=True,
            minimum_schema_coverage=0.65,
        ),
    )


def test_run_extraction_pipeline_returns_audited_refusal_without_downstream_stages(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        source_path = tmp_path / "source.txt"
        source_path.write_text("Revenue increased.", encoding="utf-8")
        output_path = tmp_path / "refusal.json"
        llm_client = RefusalLLMClient()

        result = await run_extraction_pipeline(
            source_path=source_path,
            output_path=output_path,
            config=make_strict_config(tmp_path),
            llm_client=llm_client,
            run_id="run-1",
        )

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            stored_manifest = await audit_store.get_run_manifest("run-1")
            stage_states = await audit_store.list_run_stage_states("run-1")
            candidates = await audit_store.list_lens_candidates("run-1")
            data_points = await audit_store.list_data_points("run-1")
            llm_logs = await audit_store.list_llm_call_logs("run-1")

        payload = json.loads(output_path.read_text(encoding="utf-8"))
        planner_state = next(state for state in stage_states if state.stage == "planner")
        assert result.completed_manifest == stored_manifest
        assert result.completed_manifest.status == "refused"
        assert result.refusal.reason_codes == ("no_approved_schema_candidates",)
        assert planner_state.planning_refusal == result.refusal
        assert [state.stage for state in stage_states] == [
            "ingestion",
            "chunker",
            "planner",
            "reporter",
        ]
        assert candidates == ()
        assert data_points == ()
        assert [call.stage for call in llm_client.calls] == ["planner.classify_document"]
        assert [log.stage for log in llm_logs] == ["planner.classify_document"]
        assert payload["outcome_type"] == "schema_fit_refusal"
        assert payload["refusal"]["candidate_schema_ids"] == []

    import asyncio

    asyncio.run(run_check())


def test_run_extraction_pipeline_refuses_to_resume_terminal_refusal(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        source_path = tmp_path / "source.txt"
        source_path.write_text("Revenue increased.", encoding="utf-8")
        config = make_strict_config(tmp_path)

        await run_extraction_pipeline(
            source_path=source_path,
            output_path=tmp_path / "refusal.json",
            config=config,
            llm_client=RefusalLLMClient(),
            run_id="run-1",
        )

        with pytest.raises(OrchestratorError, match="already refused"):
            await run_extraction_pipeline(
                source_path=source_path,
                output_path=tmp_path / "refusal-2.json",
                config=config,
                llm_client=RefusalLLMClient(),
                run_id="run-1",
                resume=True,
            )

    import asyncio

    asyncio.run(run_check())
