from __future__ import annotations

from extractor.audit.base import SQLiteAuditStore, UsageSummary
from extractor.audit.models import RunStageName, RunStageState
from extractor.contracts import Chunk, Document, ExtractionPlan, LLMCallLog, RunManifest


class CoreAuditRecords(SQLiteAuditStore):
    async def record_run_manifest(self, manifest: RunManifest) -> None:
        values = manifest.model_dump(mode="json")
        await self._insert_payload(
            "run_manifests",
            {
                "run_id": manifest.run_id,
                "doc_id": manifest.doc_id,
                "status": manifest.status,
                "started_at": values["started_at"],
                "completed_at": values["completed_at"],
                "payload_json": manifest.model_dump_json(),
            },
        )

    async def update_run_manifest(self, manifest: RunManifest) -> None:
        values = manifest.model_dump(mode="json")
        await self._update_payload(
            "run_manifests",
            "run_id",
            manifest.run_id,
            {
                "doc_id": manifest.doc_id,
                "status": manifest.status,
                "started_at": values["started_at"],
                "completed_at": values["completed_at"],
                "payload_json": manifest.model_dump_json(),
            },
        )

    async def get_run_manifest(self, run_id: str) -> RunManifest | None:
        return await self._fetch_payload("run_manifests", "run_id", run_id, RunManifest)

    async def list_run_manifests(self) -> tuple[RunManifest, ...]:
        return await self._list_payloads(
            "run_manifests",
            RunManifest,
            "1 = 1",
            (),
            "started_at DESC, run_id ASC",
        )

    async def record_run_stage_state(self, state: RunStageState) -> None:
        values = state.model_dump(mode="json")
        await self._insert_payload(
            "run_stage_states",
            {
                "run_id": state.run_id,
                "stage": state.stage,
                "completed_at": values["completed_at"],
                "payload_json": state.model_dump_json(),
            },
        )

    async def get_run_stage_state(
        self,
        run_id: str,
        stage: RunStageName,
    ) -> RunStageState | None:
        row = await self._fetch_one(
            "SELECT payload_json FROM run_stage_states WHERE run_id = ? AND stage = ?",
            (run_id, stage),
        )
        if row is None:
            return None
        return RunStageState.model_validate_json(row["payload_json"])

    async def list_run_stage_states(self, run_id: str) -> tuple[RunStageState, ...]:
        return await self._list_payloads(
            "run_stage_states",
            RunStageState,
            "run_id = ?",
            (run_id,),
            "completed_at ASC, stage ASC",
        )

    async def record_document(self, document: Document) -> None:
        await self._insert_payload_idempotent(
            "documents",
            "doc_id",
            document.doc_id,
            {
                "doc_id": document.doc_id,
                "source_path": document.source_path,
                "format": document.format,
                "source_sha256": document.source_sha256,
                "text_sha256": document.text_sha256,
                "payload_json": document.model_dump_json(),
            },
        )

    async def get_document(self, doc_id: str) -> Document | None:
        return await self._fetch_payload("documents", "doc_id", doc_id, Document)

    async def record_chunk(self, chunk: Chunk) -> None:
        await self._insert_payload_idempotent(
            "chunks",
            "chunk_id",
            chunk.chunk_id,
            {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "chunk_index": chunk.chunk_index,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                "payload_json": chunk.model_dump_json(),
            },
        )

    async def get_chunk(self, chunk_id: str) -> Chunk | None:
        return await self._fetch_payload("chunks", "chunk_id", chunk_id, Chunk)

    async def list_chunks(self, doc_id: str) -> tuple[Chunk, ...]:
        return await self._list_payloads(
            "chunks",
            Chunk,
            "doc_id = ?",
            (doc_id,),
            "chunk_index ASC",
        )

    async def record_extraction_plan(self, plan: ExtractionPlan) -> None:
        await self._insert_payload(
            "extraction_plans",
            {
                "run_id": plan.run_id,
                "doc_id": plan.doc_id,
                "payload_json": plan.model_dump_json(),
            },
        )

    async def get_extraction_plan(self, run_id: str) -> ExtractionPlan | None:
        return await self._fetch_payload("extraction_plans", "run_id", run_id, ExtractionPlan)

    async def record_llm_call_log(self, log: LLMCallLog) -> None:
        values = log.model_dump(mode="json")
        await self._insert_payload(
            "llm_call_logs",
            {
                "call_id": log.call_id,
                "run_id": log.run_id,
                "stage": log.stage,
                "attempt": log.attempt,
                "created_at": values["created_at"],
                "payload_json": log.model_dump_json(),
            },
        )

    async def get_llm_call_log(self, call_id: str) -> LLMCallLog | None:
        return await self._fetch_payload("llm_call_logs", "call_id", call_id, LLMCallLog)

    async def list_llm_call_logs(self, run_id: str) -> tuple[LLMCallLog, ...]:
        return await self._list_payloads(
            "llm_call_logs",
            LLMCallLog,
            "run_id = ?",
            (run_id,),
            "created_at ASC, call_id ASC",
        )

    async def summarize_run(self, run_id: str) -> UsageSummary:
        summary: UsageSummary = {}
        for log in await self.list_llm_call_logs(run_id):
            stage_summary = summary.setdefault(
                log.stage,
                {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read_tokens": 0,
                    "cache_creation_tokens": 0,
                },
            )
            stage_summary["calls"] += 1
            stage_summary["input_tokens"] += log.input_tokens
            stage_summary["output_tokens"] += log.output_tokens
            stage_summary["cache_read_tokens"] += log.cache_read_tokens
            stage_summary["cache_creation_tokens"] += log.cache_creation_tokens
        return {stage: summary[stage] for stage in sorted(summary)}


__all__ = [
    "CoreAuditRecords",
]
