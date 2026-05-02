from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path
from types import TracebackType
from typing import Any, Self, TypeVar

import aiosqlite
from pydantic import BaseModel

from extractor.audit.errors import (
    AuditIntegrityError,
    AuditNotFoundError,
    AuditSchemaError,
    AuditStoreError,
)
from extractor.audit.schema import SCHEMA_SQL, SCHEMA_VERSION


PayloadT = TypeVar("PayloadT", bound=BaseModel)
UsageSummary = dict[str, dict[str, int]]


class SQLiteAuditStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self._connection: aiosqlite.Connection | None = None

    async def __aenter__(self) -> Self:
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
        connection = self._require_connection()
        try:
            await connection.execute(sql, tuple(values[column] for column in columns))
            await connection.commit()
        except sqlite3.IntegrityError as exc:
            await connection.rollback()
            message = f"Failed to insert audit payload into {table}: {exc}"
            raise AuditIntegrityError(message) from exc

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


__all__ = [
    "SQLiteAuditStore",
    "UsageSummary",
]
