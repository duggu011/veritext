from __future__ import annotations


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


__all__ = [
    "SCHEMA_SQL",
    "SCHEMA_VERSION",
]
