from __future__ import annotations

from pathlib import Path

import pytest

from extractor.config import ReportSigningConfig, load_config
from extractor.reporter.signing import (
    ReportSigningError,
    canonical_json_sha256,
    config_sha256,
    file_sha256,
    sign_payload,
    verify_payload_signature,
)


def test_canonical_json_sha256_is_stable_across_mapping_order() -> None:
    left = {"b": 2, "a": {"d": 4, "c": 3}}
    right = {"a": {"c": 3, "d": 4}, "b": 2}

    assert canonical_json_sha256(left) == canonical_json_sha256(right)
    assert canonical_json_sha256({"items": ["a", "b"]}) != canonical_json_sha256(
        {"items": ["b", "a"]}
    )


def test_file_sha256_hashes_exact_report_bytes(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    report.write_text('{"report_schema_version":"report.v2"}\n', encoding="utf-8")

    first_hash = file_sha256(report)
    report.write_text('{"report_schema_version":"report.v2","changed":true}\n', encoding="utf-8")

    assert first_hash != file_sha256(report)


def test_config_sha256_is_stable_and_does_not_include_process_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_config(env={}, include_local=False)
    first_hash = config_sha256(config)

    monkeypatch.setenv("REPORT_SIGNING_KEY", "super-secret")

    assert config_sha256(config) == first_hash
    assert config_sha256(
        config.model_copy(update={"reporting": config.reporting})
    ) == first_hash


def test_hmac_signing_verifies_exact_payload_and_rejects_tampering() -> None:
    signing = ReportSigningConfig(
        enabled=True,
        algorithm="hmac-sha256",
        key_id="phase-40-key",
        key_env="VERITEXT_PHASE40_KEY",
        manifest_suffix=".manifest.json",
    )
    env = {"VERITEXT_PHASE40_KEY": "test-signing-secret"}
    payload = {
        "artifact_sha256": "a" * 64,
        "run_id": "run-1",
        "nested": {"b": 2, "a": 1},
    }

    signature = sign_payload(payload, signing=signing, env=env)

    assert signature.signature_algorithm == "hmac-sha256"
    assert signature.key_id == "phase-40-key"
    assert signature.signed_payload_sha256 == canonical_json_sha256(payload)
    assert verify_payload_signature(payload, signature=signature, signing=signing, env=env)
    assert not verify_payload_signature(
        {**payload, "run_id": "run-tampered"},
        signature=signature,
        signing=signing,
        env=env,
    )

    with pytest.raises(ReportSigningError, match="VERITEXT_PHASE40_KEY"):
        sign_payload(payload, signing=signing, env={})
