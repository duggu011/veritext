import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "prepare_failed_run_resume.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location(
        "prepare_failed_run_resume",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_audit_db(path: Path, *, status: str = "completed") -> None:
    manifest = {
        "run_id": "run-1",
        "doc_id": "doc-1",
        "audit_db_path": str(path),
        "status": status,
        "started_at": "2026-05-02T00:00:00Z",
        "completed_at": "2026-05-02T00:10:00Z" if status == "completed" else None,
        "output_data_point_ids": ["datapoint-1"],
    }
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE run_manifests (
                run_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE critic_reports (run_id TEXT NOT NULL);
            CREATE TABLE verifier_reports (run_id TEXT NOT NULL);
            CREATE TABLE data_points (run_id TEXT NOT NULL);
            CREATE TABLE candidate_rejections (run_id TEXT NOT NULL, stage TEXT NOT NULL);
            CREATE TABLE llm_call_logs (run_id TEXT NOT NULL, stage TEXT NOT NULL);
            CREATE TABLE run_stage_states (run_id TEXT NOT NULL, stage TEXT NOT NULL);
            """
        )
        conn.execute(
            "INSERT INTO run_manifests VALUES (?, ?, ?, ?, ?, ?)",
            (
                manifest["run_id"],
                manifest["doc_id"],
                manifest["status"],
                manifest["started_at"],
                manifest["completed_at"],
                json.dumps(manifest),
            ),
        )
        for table in ("critic_reports", "verifier_reports", "data_points"):
            conn.execute(f"INSERT INTO {table} VALUES (?)", ("run-1",))
        for stage in ("critic", "verifier", "reconciler"):
            conn.execute("INSERT INTO candidate_rejections VALUES (?, ?)", ("run-1", stage))
            conn.execute("INSERT INTO llm_call_logs VALUES (?, ?)", ("run-1", stage))
        for stage in ("critic", "verifier", "reconciler", "reporter"):
            conn.execute("INSERT INTO run_stage_states VALUES (?, ?)", ("run-1", stage))
        conn.commit()
    finally:
        conn.close()


def test_prepare_resume_refuses_completed_run_without_explicit_allow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_path = tmp_path / "audit.sqlite3"
    make_audit_db(audit_path)
    module = load_script_module()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prepare_failed_run_resume.py",
            "--run-id",
            "run-1",
            "--audit",
            str(audit_path),
            "--apply",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        module.main()

    assert exc.value.code == 2
    conn = sqlite3.connect(audit_path)
    try:
        status = conn.execute(
            "SELECT status FROM run_manifests WHERE run_id = 'run-1'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert status == "completed"


def test_prepare_resume_allow_completed_resets_manifest_and_clears_downstream(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    audit_path = tmp_path / "audit.sqlite3"
    make_audit_db(audit_path)
    module = load_script_module()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prepare_failed_run_resume.py",
            "--run-id",
            "run-1",
            "--audit",
            str(audit_path),
            "--from-stage",
            "critic",
            "--allow-completed",
            "--apply",
        ],
    )

    assert module.main() == 0
    output = capsys.readouterr().out
    assert "completed_manifest_reset=1" in output
    assert "resume_prep=applied" in output
    assert list(tmp_path.glob("audit.sqlite3.run-1.*.bak"))

    conn = sqlite3.connect(audit_path)
    try:
        status, payload_json = conn.execute(
            "SELECT status, payload_json FROM run_manifests WHERE run_id = 'run-1'"
        ).fetchone()
        payload = json.loads(payload_json)
        assert status == "failed"
        assert payload["status"] == "failed"
        assert payload["output_data_point_ids"] == []
        assert payload["completed_at"] is not None
        for table in ("critic_reports", "verifier_reports", "data_points"):
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM candidate_rejections").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM llm_call_logs").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM run_stage_states").fetchone()[0] == 0
    finally:
        conn.close()
