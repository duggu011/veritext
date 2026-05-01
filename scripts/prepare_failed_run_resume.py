"""Prepare a failed run for safe resume from the critic stage.

This script is local-only and makes no API calls. By default it only reports
what it would remove. Pass `--apply` to back up the audit DB and delete partial
critic/verifier/reconciler/reporter artifacts for one failed run id, leaving
ingestion, chunker, planner, executor, and dedup audit state intact.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


STAGE_STATE_DELETE = ("critic", "verifier", "reconciler", "reporter")
REJECTION_DELETE = ("critic", "verifier", "reconciler")
LLM_STAGE_DELETE = ("critic", "verifier", "reconciler")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--audit",
        type=Path,
        default=Path(".veritext/audit.sqlite3"),
        help="Audit SQLite DB path. Default: .veritext/audit.sqlite3.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually back up and modify the audit DB. Omit for dry-run.",
    )
    args = parser.parse_args()

    if not args.audit.exists():
        parser.error(f"audit DB not found: {args.audit}")

    conn = sqlite3.connect(args.audit)
    try:
        manifest = conn.execute(
            "SELECT status FROM run_manifests WHERE run_id = ?",
            (args.run_id,),
        ).fetchone()
        if manifest is None:
            parser.error(f"run_id not found in run_manifests: {args.run_id}")
        if manifest[0] == "completed":
            parser.error(f"refusing to prepare completed run: {args.run_id}")

        counts = _counts(conn, args.run_id)
        print(f"run_id={args.run_id}")
        print(f"manifest_status={manifest[0]}")
        for label, count in counts:
            print(f"{label}={count}")

        if not args.apply:
            print("dry_run=true")
            print("pass --apply to back up the DB and remove these partial rows")
            return 0

        backup_path = _backup_path(args.audit, args.run_id)
        shutil.copy2(args.audit, backup_path)
        print(f"backup={backup_path}")

        with conn:
            _delete_partial_rows(conn, args.run_id)
        print("resume_prep=applied")
        return 0
    finally:
        conn.close()


def _counts(conn: sqlite3.Connection, run_id: str) -> list[tuple[str, int]]:
    return [
        ("critic_reports", _count(conn, "critic_reports", "run_id = ?", (run_id,))),
        (
            "verifier_reports",
            _count(conn, "verifier_reports", "run_id = ?", (run_id,)),
        ),
        ("data_points", _count(conn, "data_points", "run_id = ?", (run_id,))),
        (
            "candidate_rejections_critic_later",
            _count(
                conn,
                "candidate_rejections",
                f"run_id = ? AND stage IN ({_placeholders(REJECTION_DELETE)})",
                (run_id, *REJECTION_DELETE),
            ),
        ),
        (
            "llm_call_logs_critic_later",
            _count(
                conn,
                "llm_call_logs",
                f"run_id = ? AND stage IN ({_placeholders(LLM_STAGE_DELETE)})",
                (run_id, *LLM_STAGE_DELETE),
            ),
        ),
        (
            "run_stage_states_critic_later",
            _count(
                conn,
                "run_stage_states",
                f"run_id = ? AND stage IN ({_placeholders(STAGE_STATE_DELETE)})",
                (run_id, *STAGE_STATE_DELETE),
            ),
        ),
    ]


def _count(
    conn: sqlite3.Connection,
    table: str,
    where: str,
    params: tuple[object, ...],
) -> int:
    row = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", params).fetchone()
    if row is None:
        return 0
    return int(row[0])


def _delete_partial_rows(conn: sqlite3.Connection, run_id: str) -> None:
    conn.execute("DELETE FROM critic_reports WHERE run_id = ?", (run_id,))
    conn.execute("DELETE FROM verifier_reports WHERE run_id = ?", (run_id,))
    conn.execute("DELETE FROM data_points WHERE run_id = ?", (run_id,))
    conn.execute(
        f"DELETE FROM candidate_rejections WHERE run_id = ? "
        f"AND stage IN ({_placeholders(REJECTION_DELETE)})",
        (run_id, *REJECTION_DELETE),
    )
    conn.execute(
        f"DELETE FROM llm_call_logs WHERE run_id = ? "
        f"AND stage IN ({_placeholders(LLM_STAGE_DELETE)})",
        (run_id, *LLM_STAGE_DELETE),
    )
    conn.execute(
        f"DELETE FROM run_stage_states WHERE run_id = ? "
        f"AND stage IN ({_placeholders(STAGE_STATE_DELETE)})",
        (run_id, *STAGE_STATE_DELETE),
    )


def _placeholders(values: tuple[str, ...]) -> str:
    return ", ".join("?" for _value in values)


def _backup_path(audit_path: Path, run_id: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe_run_id = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in run_id)
    return audit_path.with_name(f"{audit_path.name}.{safe_run_id}.{stamp}.bak")


if __name__ == "__main__":
    raise SystemExit(main())
