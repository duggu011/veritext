"""Prepare a failed or explicitly opted-in completed run for safe resume.

This script is local-only and makes no API calls. By default it only reports
what it would remove. Pass `--apply` to back up the audit DB and delete partial
artifacts for one run id, leaving earlier completed audit state intact.

Completed runs are refused unless `--allow-completed` is supplied. That option
exists for deliberate downstream remeasurement only; when applied it resets the
manifest to a failed, resumable state and clears old output data point IDs.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


STAGE_ORDER = ("planner", "executor", "dedup", "critic", "verifier", "reconciler")
REPORT_STAGE_ORDER = (
    "planner",
    "executor",
    "dedup",
    "critic",
    "verifier",
    "reconciler",
    "reporter",
)
REJECTION_STAGES = ("executor", "dedup", "critic", "verifier", "reconciler")
LLM_STAGE_PREFIXES = {
    "planner": "planner.",
    "executor": "executor.",
}


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
    parser.add_argument(
        "--from-stage",
        choices=STAGE_ORDER,
        default="critic",
        help=(
            "First stage to clear. Default keeps old behavior and clears "
            "critic and later. Use planner after prompt/schema changes to "
            "force a new plan plus all downstream artifacts. Use verifier "
            "after a partial verifier rate-limit failure to preserve completed "
            "critic work."
        ),
    )
    parser.add_argument(
        "--allow-completed",
        action="store_true",
        help=(
            "Allow deliberate cleanup of a completed run. Requires --apply to "
            "mutate the DB; dry-run shows the rows and manifest reset that "
            "would occur."
        ),
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
        completed_run = manifest[0] == "completed"
        if completed_run and not args.allow_completed:
            parser.error(f"refusing to prepare completed run: {args.run_id}")

        counts = _counts(conn, args.run_id, from_stage=args.from_stage)
        print(f"run_id={args.run_id}")
        print(f"manifest_status={manifest[0]}")
        print(f"from_stage={args.from_stage}")
        if completed_run:
            print("completed_manifest_reset=1")
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
            _delete_partial_rows(conn, args.run_id, from_stage=args.from_stage)
            if completed_run:
                _reset_manifest_for_resume(conn, args.run_id)
        print("resume_prep=applied")
        return 0
    finally:
        conn.close()


def _counts(
    conn: sqlite3.Connection,
    run_id: str,
    *,
    from_stage: str,
) -> list[tuple[str, int]]:
    stage_delete = _stages_from(from_stage, STAGE_ORDER)
    stage_state_delete = _stages_from(from_stage, REPORT_STAGE_ORDER)
    counts: list[tuple[str, int]] = []
    if "planner" in stage_delete:
        counts.append(
            (
                "extraction_plans",
                _count(conn, "extraction_plans", "run_id = ?", (run_id,)),
            )
        )
    if "executor" in stage_delete:
        counts.append(
            ("lens_candidates", _count(conn, "lens_candidates", "run_id = ?", (run_id,)))
        )
    if "critic" in stage_delete:
        counts.append(
            ("critic_reports", _count(conn, "critic_reports", "run_id = ?", (run_id,)))
        )
    if "verifier" in stage_delete:
        counts.append(
            (
                "verifier_reports",
                _count(conn, "verifier_reports", "run_id = ?", (run_id,)),
            )
        )
    if "reconciler" in stage_delete:
        counts.append(("data_points", _count(conn, "data_points", "run_id = ?", (run_id,))))
    counts.extend(
        [
            (
                "candidate_rejections_from_stage",
                _count(
                    conn,
                    "candidate_rejections",
                    f"run_id = ? AND stage IN ({_placeholders(_rejection_stages(stage_delete))})",
                    (run_id, *_rejection_stages(stage_delete)),
                ),
            ),
            (
                "llm_call_logs_from_stage",
                _count(
                    conn,
                    "llm_call_logs",
                    f"run_id = ? AND ({_stage_where_clause(stage_delete)})",
                    (run_id, *_stage_where_params(stage_delete)),
                ),
            ),
            (
                "run_stage_states_from_stage",
                _count(
                    conn,
                    "run_stage_states",
                    f"run_id = ? AND stage IN ({_placeholders(stage_state_delete)})",
                    (run_id, *stage_state_delete),
                ),
            ),
        ]
    )
    return [
        item for item in counts if item[1] > 0 or item[0].endswith("_from_stage")
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


def _delete_partial_rows(
    conn: sqlite3.Connection,
    run_id: str,
    *,
    from_stage: str,
) -> None:
    stage_delete = _stages_from(from_stage, STAGE_ORDER)
    stage_state_delete = _stages_from(from_stage, REPORT_STAGE_ORDER)
    if "critic" in stage_delete:
        conn.execute("DELETE FROM critic_reports WHERE run_id = ?", (run_id,))
    if "verifier" in stage_delete:
        conn.execute("DELETE FROM verifier_reports WHERE run_id = ?", (run_id,))
    if "reconciler" in stage_delete:
        conn.execute("DELETE FROM data_points WHERE run_id = ?", (run_id,))
    rejection_stages = _rejection_stages(stage_delete)
    conn.execute(
        f"DELETE FROM candidate_rejections WHERE run_id = ? "
        f"AND stage IN ({_placeholders(rejection_stages)})",
        (run_id, *rejection_stages),
    )
    conn.execute(
        f"DELETE FROM llm_call_logs WHERE run_id = ? "
        f"AND ({_stage_where_clause(stage_delete)})",
        (run_id, *_stage_where_params(stage_delete)),
    )
    if "executor" in stage_delete:
        conn.execute("DELETE FROM lens_candidates WHERE run_id = ?", (run_id,))
    if "planner" in stage_delete:
        conn.execute("DELETE FROM extraction_plans WHERE run_id = ?", (run_id,))
    conn.execute(
        f"DELETE FROM run_stage_states WHERE run_id = ? "
        f"AND stage IN ({_placeholders(stage_state_delete)})",
        (run_id, *stage_state_delete),
    )


def _reset_manifest_for_resume(conn: sqlite3.Connection, run_id: str) -> None:
    row = conn.execute(
        "SELECT payload_json FROM run_manifests WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"run_id not found in run_manifests: {run_id}")

    reset_at = datetime.now(timezone.utc).isoformat()
    payload = json.loads(row[0])
    payload["status"] = "failed"
    payload["completed_at"] = reset_at
    payload["output_data_point_ids"] = []
    conn.execute(
        "UPDATE run_manifests "
        "SET status = ?, completed_at = ?, payload_json = ? "
        "WHERE run_id = ?",
        ("failed", reset_at, json.dumps(payload), run_id),
    )


def _stages_from(from_stage: str, order: tuple[str, ...]) -> tuple[str, ...]:
    start = order.index(from_stage)
    return order[start:]


def _rejection_stages(stages: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(stage for stage in stages if stage in REJECTION_STAGES)


def _stage_where_clause(stages: tuple[str, ...]) -> str:
    clauses: list[str] = []
    for stage in stages:
        prefix = LLM_STAGE_PREFIXES.get(stage)
        clauses.append("stage LIKE ?" if prefix is not None else "stage = ?")
    return " OR ".join(clauses)


def _stage_where_params(stages: tuple[str, ...]) -> tuple[str, ...]:
    params: list[str] = []
    for stage in stages:
        prefix = LLM_STAGE_PREFIXES.get(stage)
        params.append(f"{prefix}%" if prefix is not None else stage)
    return tuple(params)


def _placeholders(values: tuple[str, ...]) -> str:
    return ", ".join("?" for _value in values)


def _backup_path(audit_path: Path, run_id: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe_run_id = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in run_id)
    return audit_path.with_name(f"{audit_path.name}.{safe_run_id}.{stamp}.bak")


if __name__ == "__main__":
    raise SystemExit(main())
