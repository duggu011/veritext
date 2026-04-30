from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path
from types import TracebackType
from typing import Any, TypeVar

import aiosqlite
from pydantic import BaseModel

from extractor.audit.models import CandidateRejection, RunStageName, RunStageState
from extractor.contracts import (
    Chunk,
    CriticReport,
    DataPoint,
    Document,
    ExtractionPlan,
    LLMCallLog,
    LensCandidate,
    RunManifest,
    VerifierReport,
)


SCHEMA_VERSION = "1"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS audit_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS run_manifests (
    run_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    source_path TEXT NOT NULL,
    format TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    text_sha256 TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    UNIQUE (doc_id, chunk_index),
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
);

CREATE TABLE IF NOT EXISTS extraction_plans (
    run_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES run_manifests(run_id),
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
);

CREATE TABLE IF NOT EXISTS llm_call_logs (
    call_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES run_manifests(run_id)
);

CREATE TABLE IF NOT EXISTS lens_candidates (
    candidate_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    chunk_id TEXT NOT NULL,
    category TEXT NOT NULL,
    field_name TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES run_manifests(run_id),
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id),
    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id)
);

CREATE TABLE IF NOT EXISTS critic_reports (
    report_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    accepted INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES run_manifests(run_id),
    FOREIGN KEY (candidate_id) REFERENCES lens_candidates(candidate_id)
);

CREATE TABLE IF NOT EXISTS verifier_reports (
    report_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    accepted INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES run_manifests(run_id),
    FOREIGN KEY (candidate_id) REFERENCES lens_candidates(candidate_id)
);

CREATE TABLE IF NOT EXISTS data_points (
    data_point_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    category TEXT NOT NULL,
    field_name TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES run_manifests(run_id),
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
);

CREATE TABLE IF NOT EXISTS candidate_rejections (
    rejection_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES run_manifests(run_id),
    FOREIGN KEY (candidate_id) REFERENCES lens_candidates(candidate_id)
);

CREATE TABLE IF NOT EXISTS run_stage_states (
    run_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (run_id, stage),
    FOREIGN KEY (run_id) REFERENCES run_manifests(run_id)
);
"""


PayloadT = TypeVar("PayloadT", bound=BaseModel)
UsageSummary = dict[str, dict[str, int]]


class AuditStoreError(RuntimeError):
    """Base class for audit storage failures."""


class AuditSchemaError(AuditStoreError):
    """Raised when an audit database schema is incompatible."""


class AuditIntegrityError(AuditStoreError):
    """Raised when an audit write would violate identity or provenance constraints."""


class AuditNotFoundError(AuditStoreError):
    """Raised when an explicit audit update targets a missing record."""


class AuditStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self._connection: aiosqlite.Connection | None = None

    async def __aenter__(self) -> AuditStore:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    async def connect(self) -> None:
        if self._connection is not None:
            return

        if str(self.database_path) != ":memory:":
            self.database_path.parent.mkdir(parents=True, exist_ok=True)

        connection = await aiosqlite.connect(str(self.database_path))
        connection.row_factory = aiosqlite.Row
        await connection.execute("PRAGMA foreign_keys = ON")
        self._connection = connection
        await self.initialize()

    async def close(self) -> None:
        if self._connection is None:
            return
        await self._connection.close()
        self._connection = None

    async def initialize(self) -> None:
        connection = self._require_connection()
        await connection.executescript(SCHEMA_SQL)
        await self._ensure_schema_version()
        await connection.commit()

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

    async def record_lens_candidate(self, candidate: LensCandidate) -> None:
        await self._insert_payload(
            "lens_candidates",
            {
                "candidate_id": candidate.candidate_id,
                "run_id": candidate.run_id,
                "doc_id": candidate.doc_id,
                "chunk_id": candidate.chunk_id,
                "category": candidate.category,
                "field_name": candidate.field_name,
                "payload_json": candidate.model_dump_json(),
            },
        )

    async def get_lens_candidate(self, candidate_id: str) -> LensCandidate | None:
        return await self._fetch_payload(
            "lens_candidates",
            "candidate_id",
            candidate_id,
            LensCandidate,
        )

    async def list_lens_candidates(self, run_id: str) -> tuple[LensCandidate, ...]:
        return await self._list_payloads(
            "lens_candidates",
            LensCandidate,
            "run_id = ?",
            (run_id,),
            "candidate_id ASC",
        )

    async def record_critic_report(self, report: CriticReport) -> None:
        await self._insert_payload(
            "critic_reports",
            {
                "report_id": report.report_id,
                "run_id": report.run_id,
                "candidate_id": report.candidate_id,
                "accepted": int(report.accepted),
                "payload_json": report.model_dump_json(),
            },
        )

    async def get_critic_report(self, report_id: str) -> CriticReport | None:
        return await self._fetch_payload("critic_reports", "report_id", report_id, CriticReport)

    async def list_critic_reports(self, candidate_id: str) -> tuple[CriticReport, ...]:
        return await self._list_payloads(
            "critic_reports",
            CriticReport,
            "candidate_id = ?",
            (candidate_id,),
            "report_id ASC",
        )

    async def list_critic_reports_for_run(self, run_id: str) -> tuple[CriticReport, ...]:
        return await self._list_payloads(
            "critic_reports",
            CriticReport,
            "run_id = ?",
            (run_id,),
            "candidate_id ASC, report_id ASC",
        )

    async def record_verifier_report(self, report: VerifierReport) -> None:
        await self._insert_payload(
            "verifier_reports",
            {
                "report_id": report.report_id,
                "run_id": report.run_id,
                "candidate_id": report.candidate_id,
                "accepted": int(report.accepted),
                "payload_json": report.model_dump_json(),
            },
        )

    async def get_verifier_report(self, report_id: str) -> VerifierReport | None:
        return await self._fetch_payload(
            "verifier_reports",
            "report_id",
            report_id,
            VerifierReport,
        )

    async def list_verifier_reports(self, candidate_id: str) -> tuple[VerifierReport, ...]:
        return await self._list_payloads(
            "verifier_reports",
            VerifierReport,
            "candidate_id = ?",
            (candidate_id,),
            "report_id ASC",
        )

    async def list_verifier_reports_for_run(self, run_id: str) -> tuple[VerifierReport, ...]:
        return await self._list_payloads(
            "verifier_reports",
            VerifierReport,
            "run_id = ?",
            (run_id,),
            "candidate_id ASC, report_id ASC",
        )

    async def record_data_point(self, data_point: DataPoint) -> None:
        await self._insert_payload(
            "data_points",
            {
                "data_point_id": data_point.data_point_id,
                "run_id": data_point.run_id,
                "doc_id": data_point.doc_id,
                "category": data_point.category,
                "field_name": data_point.field_name,
                "payload_json": data_point.model_dump_json(),
            },
        )

    async def get_data_point(self, data_point_id: str) -> DataPoint | None:
        return await self._fetch_payload("data_points", "data_point_id", data_point_id, DataPoint)

    async def list_data_points(self, run_id: str) -> tuple[DataPoint, ...]:
        return await self._list_payloads(
            "data_points",
            DataPoint,
            "run_id = ?",
            (run_id,),
            "data_point_id ASC",
        )

    async def record_candidate_rejection(self, rejection: CandidateRejection) -> None:
        values = rejection.model_dump(mode="json")
        await self._insert_payload(
            "candidate_rejections",
            {
                "rejection_id": rejection.rejection_id,
                "run_id": rejection.run_id,
                "candidate_id": rejection.candidate_id,
                "stage": rejection.stage,
                "created_at": values["created_at"],
                "payload_json": rejection.model_dump_json(),
            },
        )

    async def get_candidate_rejection(self, rejection_id: str) -> CandidateRejection | None:
        return await self._fetch_payload(
            "candidate_rejections",
            "rejection_id",
            rejection_id,
            CandidateRejection,
        )

    async def list_candidate_rejections(self, candidate_id: str) -> tuple[CandidateRejection, ...]:
        return await self._list_payloads(
            "candidate_rejections",
            CandidateRejection,
            "candidate_id = ?",
            (candidate_id,),
            "created_at ASC, rejection_id ASC",
        )

    async def list_candidate_rejections_for_run(
        self,
        run_id: str,
    ) -> tuple[CandidateRejection, ...]:
        return await self._list_payloads(
            "candidate_rejections",
            CandidateRejection,
            "run_id = ?",
            (run_id,),
            "stage ASC, candidate_id ASC, created_at ASC, rejection_id ASC",
        )

    async def get_schema_version(self) -> str | None:
        row = await self._fetch_one(
            "SELECT value FROM audit_metadata WHERE key = ?",
            ("schema_version",),
        )
        if row is None:
            return None
        return str(row["value"])

    async def _ensure_schema_version(self) -> None:
        connection = self._require_connection()
        row = await self._fetch_one(
            "SELECT value FROM audit_metadata WHERE key = ?",
            ("schema_version",),
        )
        if row is None:
            await connection.execute(
                "INSERT INTO audit_metadata (key, value) VALUES (?, ?)",
                ("schema_version", SCHEMA_VERSION),
            )
            await connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            return
        if row["value"] != SCHEMA_VERSION:
            raise AuditSchemaError(
                f"Unsupported audit schema version {row['value']}; expected {SCHEMA_VERSION}"
            )
        await connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    async def _insert_payload(self, table: str, values: dict[str, Any]) -> None:
        columns = tuple(values.keys())
        placeholders = ", ".join("?" for _ in columns)
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        try:
            await self._require_connection().execute(sql, tuple(values[column] for column in columns))
            await self._require_connection().commit()
        except sqlite3.IntegrityError as exc:
            await self._require_connection().rollback()
            raise AuditIntegrityError(f"Failed to insert audit payload into {table}: {exc}") from exc

    async def _insert_payload_idempotent(
        self,
        table: str,
        key_column: str,
        key_value: str,
        values: dict[str, Any],
    ) -> None:
        try:
            await self._insert_payload(table, values)
        except AuditIntegrityError as exc:
            existing = await self._fetch_payload_json(table, key_column, key_value)
            if existing is not None and existing == values["payload_json"]:
                return
            raise exc

    async def _update_payload(
        self,
        table: str,
        key_column: str,
        key_value: str,
        values: dict[str, Any],
    ) -> None:
        assignments = ", ".join(f"{column} = ?" for column in values)
        sql = f"UPDATE {table} SET {assignments} WHERE {key_column} = ?"
        try:
            cursor = await self._require_connection().execute(
                sql,
                (*values.values(), key_value),
            )
            if cursor.rowcount == 0:
                await self._require_connection().rollback()
                raise AuditNotFoundError(f"Missing audit payload in {table}: {key_value}")
            await self._require_connection().commit()
        except sqlite3.IntegrityError as exc:
            await self._require_connection().rollback()
            raise AuditIntegrityError(f"Failed to update audit payload in {table}: {exc}") from exc

    async def _fetch_payload(
        self,
        table: str,
        key_column: str,
        key_value: str,
        model_type: type[PayloadT],
    ) -> PayloadT | None:
        row = await self._fetch_one(
            f"SELECT payload_json FROM {table} WHERE {key_column} = ?",
            (key_value,),
        )
        if row is None:
            return None
        return model_type.model_validate_json(row["payload_json"])

    async def _fetch_payload_json(
        self,
        table: str,
        key_column: str,
        key_value: str,
    ) -> str | None:
        row = await self._fetch_one(
            f"SELECT payload_json FROM {table} WHERE {key_column} = ?",
            (key_value,),
        )
        if row is None:
            return None
        return str(row["payload_json"])

    async def _list_payloads(
        self,
        table: str,
        model_type: type[PayloadT],
        where_sql: str,
        params: Iterable[Any],
        order_by: str,
    ) -> tuple[PayloadT, ...]:
        cursor = await self._require_connection().execute(
            f"SELECT payload_json FROM {table} WHERE {where_sql} ORDER BY {order_by}",
            tuple(params),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return tuple(model_type.model_validate_json(row["payload_json"]) for row in rows)

    async def _fetch_one(self, sql: str, params: Iterable[Any]) -> aiosqlite.Row | None:
        cursor = await self._require_connection().execute(sql, tuple(params))
        row = await cursor.fetchone()
        await cursor.close()
        return row

    def _require_connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            raise AuditStoreError("Audit store is not connected")
        return self._connection


async def open_audit_store(database_path: str | Path) -> AuditStore:
    store = AuditStore(database_path)
    await store.connect()
    return store


__all__ = [
    "AuditIntegrityError",
    "AuditNotFoundError",
    "AuditSchemaError",
    "AuditStore",
    "AuditStoreError",
    "UsageSummary",
    "open_audit_store",
]
