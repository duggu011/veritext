import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from extractor.audit import AuditStore
from extractor.config import (
    AuditConfig,
    ChunkingConfig,
    ExecutionConfig,
    ExtractorConfig,
    LLMConfig,
    LoggingConfig,
    PromptConfig,
)
from extractor.contracts import LLMCallLog
from extractor.llm import StructuredLLMResult
from extractor.orchestrator import run_extraction_pipeline


ROOT = Path(__file__).resolve().parents[2]
HASH = "a" * 64


class DeterministicLLMClient:
    def __init__(self, *, reject_planner_schema: bool = False) -> None:
        self.reject_planner_schema = reject_planner_schema
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
            input_tokens=10 + len(self.calls),
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
        output = output_model.model_validate(self._payload_for_request(request))
        return StructuredLLMResult(output=output, call_log=call_log)

    def _payload_for_request(self, request: object) -> dict[str, object]:
        if request.stage == "planner.classify_document":
            return {
                "document_type": "financial_update",
                "summary": "Financial update.",
                "domain_hints": ("finance",),
                "confidence": 0.9,
            }
        if request.stage == "planner.propose_schema":
            return {"categories": (approved_category(),), "rationale": "Document has findings."}
        if request.stage == "planner.critique_schema":
            if self.reject_planner_schema:
                return {
                    "accepted": False,
                    "approved_categories": (),
                    "issues": ("No stable schema should be accepted.",),
                }
            return {"accepted": True, "approved_categories": (approved_category(),), "issues": ()}
        if request.stage == "planner.select_strategy":
            return {"enabled_lenses": ("claim",), "rationale": "Claims capture findings."}
        if request.stage == "planner.allocate_budget":
            return {
                "budget": {
                    "per_chunk_concurrency": 1,
                    "lens_budgets": ({"lens": "claim", "max_calls": 1},),
                }
            }
        if request.stage == "executor.claim":
            chunk = json.loads(request.user_content)["chunk"]
            source_text = "Revenue increased"
            return {
                "candidates": (
                    {
                        "category": "Finding",
                        "field_name": "summary",
                        "value": source_text,
                        "source_text": source_text,
                        "start_char": chunk["start_char"],
                        "confidence": 0.8,
                    },
                )
            }
        if request.stage == "critic":
            candidate_ids = [
                item["candidate_id"]
                for item in json.loads(request.user_content)["candidates"]
            ]
            return {
                "reports": tuple(
                    {
                        "candidate_id": candidate_id,
                        "plausibility_score": 0.9,
                        "accepted": True,
                        "issues": (),
                        "corrected_candidate": None,
                    }
                    for candidate_id in candidate_ids
                ),
            }
        if request.stage == "verifier":
            candidate_ids = [
                item["candidate"]["candidate_id"]
                for item in json.loads(request.user_content)["items"]
            ]
            return {
                "reports": tuple(
                    {
                        "candidate_id": candidate_id,
                        "span_verified": True,
                        "category_verified": True,
                        "alignment_score": 0.92,
                        "accepted": True,
                        "rejection_reasons": (),
                    }
                    for candidate_id in candidate_ids
                ),
            }
        if request.stage == "reconciler":
            candidate_id = json.loads(request.user_content)["candidates"][0]["candidate_id"]
            return {
                "data_points": (
                    {
                        "category": "Finding",
                        "field_name": "summary",
                        "value": "Revenue increased",
                        "source_candidate_id": candidate_id,
                        "contributing_candidate_ids": (candidate_id,),
                        "confidence": 0.95,
                    },
                ),
                "rejected_candidates": (),
            }
        raise AssertionError(f"Unhandled stage: {request.stage}")


def approved_category() -> dict[str, object]:
    return {
        "name": "Finding",
        "description": "A source-backed finding.",
        "fields": (
            {
                "name": "summary",
                "description": "Short finding summary.",
                "value_type": "text",
                "required": True,
            },
        ),
    }


def make_config(tmp_path: Path) -> ExtractorConfig:
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
    )


def test_run_extraction_pipeline_wires_all_stages_and_completes_manifest(tmp_path: Path) -> None:
    async def run_check() -> None:
        source_path = tmp_path / "source.txt"
        source_path.write_text("Revenue increased.", encoding="utf-8")
        output_path = tmp_path / "report.json"
        llm_client = DeterministicLLMClient()

        result = await run_extraction_pipeline(
            source_path=source_path,
            output_path=output_path,
            config=make_config(tmp_path),
            llm_client=llm_client,
            run_id="run-1",
            domain_hints=("user-hint",),
        )

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            stored_manifest = await audit_store.get_run_manifest("run-1")
            stored_data_points = await audit_store.list_data_points("run-1")
            llm_logs = await audit_store.list_llm_call_logs("run-1")

        payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert result.run_id == "run-1"
        assert result.document.doc_id == stored_manifest.doc_id
        assert result.plan.domain_hints == ("user-hint", "finance")
        assert len(result.chunks) == 1
        assert len(result.execution.accepted_candidates) == 1
        assert len(result.critic.accepted_candidates) == 1
        assert len(result.verification.accepted_candidates) == 1
        assert stored_data_points == result.reconciliation.data_points
        assert result.completed_manifest == stored_manifest
        assert stored_manifest.status == "completed"
        assert stored_manifest.output_data_point_ids == tuple(payload["output_data_point_ids"])
        assert payload["data_points"][0]["value"] == "Revenue increased"
        assert [log.stage for log in llm_logs] == [
            "planner.classify_document",
            "planner.propose_schema",
            "planner.critique_schema",
            "planner.select_strategy",
            "planner.allocate_budget",
            "executor.claim",
            "critic",
            "verifier",
            "reconciler",
        ]

    import asyncio

    asyncio.run(run_check())


def test_run_extraction_pipeline_marks_manifest_failed_on_stage_error(tmp_path: Path) -> None:
    async def run_check() -> None:
        source_path = tmp_path / "source.txt"
        source_path.write_text("Revenue increased.", encoding="utf-8")

        with pytest.raises(RuntimeError, match="Schema critique rejected"):
            await run_extraction_pipeline(
                source_path=source_path,
                output_path=tmp_path / "report.json",
                config=make_config(tmp_path),
                llm_client=DeterministicLLMClient(reject_planner_schema=True),
                run_id="run-1",
            )

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            stored_manifest = await audit_store.get_run_manifest("run-1")
            data_points = await audit_store.list_data_points("run-1")

        assert stored_manifest.status == "failed"
        assert stored_manifest.completed_at is not None
        assert stored_manifest.output_data_point_ids == ()
        assert data_points == ()
        assert not (tmp_path / "report.json").exists()

    import asyncio

    asyncio.run(run_check())
