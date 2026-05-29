from __future__ import annotations

import hashlib
import hmac
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from extractor.config import ExtractorConfig, ReportSigningConfig
from extractor.contracts import ReportSignatureEnvelope


class ReportSigningError(RuntimeError):
    """Raised when a requested report signature cannot be produced or verified."""


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        _json_ready(payload),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_json_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def config_sha256(config: ExtractorConfig) -> str:
    return canonical_json_sha256(config)


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sign_payload(
    payload: Any,
    *,
    signing: ReportSigningConfig,
    env: Mapping[str, str] | None = None,
) -> ReportSignatureEnvelope:
    payload_bytes = canonical_json_bytes(payload)
    return ReportSignatureEnvelope(
        signature_algorithm=signing.algorithm,
        key_id=signing.key_id,
        signed_payload_sha256=hashlib.sha256(payload_bytes).hexdigest(),
        signature=_hmac_sha256(payload_bytes, signing=signing, env=env),
    )


def verify_payload_signature(
    payload: Any,
    *,
    signature: ReportSignatureEnvelope,
    signing: ReportSigningConfig,
    env: Mapping[str, str] | None = None,
) -> bool:
    payload_bytes = canonical_json_bytes(payload)
    payload_sha256 = hashlib.sha256(payload_bytes).hexdigest()
    if signature.signature_algorithm != signing.algorithm:
        return False
    if signature.key_id != signing.key_id:
        return False
    if signature.signed_payload_sha256 != payload_sha256:
        return False

    expected_signature = _hmac_sha256(payload_bytes, signing=signing, env=env)
    return hmac.compare_digest(signature.signature, expected_signature)


def _hmac_sha256(
    payload_bytes: bytes,
    *,
    signing: ReportSigningConfig,
    env: Mapping[str, str] | None,
) -> str:
    if signing.algorithm != "hmac-sha256":
        raise ReportSigningError(f"Unsupported signing algorithm: {signing.algorithm}")
    key = (env or os.environ).get(signing.key_env)
    if key is None or key == "":
        raise ReportSigningError(f"Missing report signing key environment variable: {signing.key_env}")
    return hmac.new(key.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


def _json_ready(payload: Any) -> Any:
    if isinstance(payload, BaseModel):
        return payload.model_dump(mode="json")
    if isinstance(payload, Mapping):
        return {str(key): _json_ready(value) for key, value in payload.items()}
    if isinstance(payload, tuple | list):
        return [_json_ready(value) for value in payload]
    if isinstance(payload, Path):
        return str(payload)
    return payload


__all__ = [
    "ReportSigningError",
    "canonical_json_bytes",
    "canonical_json_sha256",
    "config_sha256",
    "file_sha256",
    "sign_payload",
    "verify_payload_signature",
]
