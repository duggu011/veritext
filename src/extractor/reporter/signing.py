from __future__ import annotations

import hashlib
import hmac
import json
import os
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from extractor.audit import AuditStore
from extractor.config import ExtractorConfig, ReportSigningConfig
from extractor.contracts import (
    AuditIntegrityEvent,
    CrossDocumentRunManifest,
    ReportArtifactRef,
    ReportConfidenceBucketSummary,
    ReportSignatureEnvelope,
    RunManifest,
    SignedReportManifest,
)
from extractor.reporter.models import CrossDocumentReport, ExtractionReport, ReportWriteResult


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


async def write_signed_report_manifest(
    *,
    report_result: ReportWriteResult,
    audit_store: AuditStore,
    config: ExtractorConfig,
    manifest_path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> SignedReportManifest:
    output_path = Path(report_result.output_path)
    artifact = _artifact_ref(report_result)
    source_sha256s, text_sha256s = await _source_hashes(report_result, audit_store)
    prompt_sha256s = await _prompt_hashes(report_result, audit_store)
    schema_hashes = _schema_hashes(report_result)
    previous_chain_hash = await audit_store.get_latest_audit_integrity_chain_hash() or ("0" * 64)
    manifest_payload = {
        "manifest_schema_version": "signed_report_manifest.v1",
        "artifact": artifact.model_dump(mode="json"),
        "source_sha256s": source_sha256s,
        "text_sha256s": text_sha256s,
        "schema_hashes": schema_hashes,
        "prompt_sha256s": prompt_sha256s,
        "config_sha256": config_sha256(config),
        "confidence_buckets": tuple(
            bucket.model_dump(mode="json")
            for bucket in _confidence_buckets(report_result, config)
        ),
        "audit_digest_sha256": _audit_digest_sha256(
            artifact=artifact,
            source_sha256s=source_sha256s,
            text_sha256s=text_sha256s,
            schema_hashes=schema_hashes,
            prompt_sha256s=prompt_sha256s,
            config_hash=config_sha256(config),
        ),
        "audit_chain_head_sha256": previous_chain_hash,
    }
    manifest = SignedReportManifest(
        **manifest_payload,
        signature=sign_payload(
            manifest_payload,
            signing=config.reporting.signing,
            env=env,
        ),
    )
    rendered = _render_manifest_json(manifest)
    path = Path(manifest_path) if manifest_path is not None else _default_manifest_path(
        output_path,
        config.reporting.signing.manifest_suffix,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")

    payload_sha256 = canonical_json_sha256(manifest)
    chain_hash = canonical_json_sha256(
        {
            "previous_chain_hash": previous_chain_hash,
            "payload_sha256": payload_sha256,
        }
    )
    await audit_store.record_audit_integrity_event(
        AuditIntegrityEvent(
            event_id=f"aie-{chain_hash[:24]}",
            event_kind="report_manifest_signed",
            run_id=artifact.run_id,
            cross_document_run_id=artifact.cross_document_run_id,
            artifact_sha256=artifact.artifact_sha256,
            payload_sha256=payload_sha256,
            previous_chain_hash=previous_chain_hash,
            chain_hash=chain_hash,
            created_at=datetime.now(timezone.utc),
            payload_json=manifest.model_dump(mode="json"),
        )
    )
    return manifest


def verify_signed_report_manifest(
    *,
    report_path: str | Path,
    manifest: SignedReportManifest,
    config: ExtractorConfig,
    env: Mapping[str, str] | None = None,
) -> bool:
    if file_sha256(report_path) != manifest.artifact.artifact_sha256:
        return False
    return verify_payload_signature(
        _manifest_signature_payload(manifest),
        signature=manifest.signature,
        signing=config.reporting.signing,
        env=env,
    )


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


def _artifact_ref(report_result: ReportWriteResult) -> ReportArtifactRef:
    completed_manifest = report_result.completed_manifest
    common = {
        "artifact_path": report_result.output_path,
        "report_schema_version": report_result.report.report_schema_version,
        "artifact_sha256": report_result.output_sha256,
        "byte_length": report_result.output_byte_length,
    }
    if isinstance(completed_manifest, RunManifest):
        return ReportArtifactRef(
            **common,
            run_id=completed_manifest.run_id,
            doc_id=completed_manifest.doc_id,
        )
    if isinstance(completed_manifest, CrossDocumentRunManifest):
        return ReportArtifactRef(
            **common,
            cross_document_run_id=completed_manifest.cross_document_run_id,
        )
    raise ReportSigningError("Unsupported report manifest type for signing")


async def _source_hashes(
    report_result: ReportWriteResult,
    audit_store: AuditStore,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    completed_manifest = report_result.completed_manifest
    if isinstance(completed_manifest, RunManifest):
        document = await audit_store.get_document(completed_manifest.doc_id)
        if document is None:
            raise ReportSigningError(f"Missing audited document: {completed_manifest.doc_id}")
        return (document.source_sha256,), (document.text_sha256,)
    if isinstance(report_result.report, CrossDocumentReport):
        source_hashes = sorted(
            {
                source.source_sha256
                for group in report_result.report.groups
                for source in group.sources
            }
        )
        text_hashes = sorted(
            {
                source.text_sha256
                for group in report_result.report.groups
                for source in group.sources
            }
        )
        return tuple(source_hashes), tuple(text_hashes)
    raise ReportSigningError("Unsupported report type for source hash collection")


async def _prompt_hashes(
    report_result: ReportWriteResult,
    audit_store: AuditStore,
) -> tuple[str, ...]:
    completed_manifest = report_result.completed_manifest
    if isinstance(completed_manifest, RunManifest):
        logs = await audit_store.list_llm_call_logs(completed_manifest.run_id)
        return tuple(sorted({log.prompt_sha256 for log in logs}))
    if isinstance(completed_manifest, CrossDocumentRunManifest):
        hashes: set[str] = set()
        for run_id in completed_manifest.input_run_ids:
            logs = await audit_store.list_llm_call_logs(run_id)
            hashes.update(log.prompt_sha256 for log in logs)
        return tuple(sorted(hashes))
    return ()


def _schema_hashes(report_result: ReportWriteResult) -> tuple[str, ...]:
    if isinstance(report_result.report, ExtractionReport):
        return (report_result.report.schema_metadata.schema_hash,)
    if isinstance(report_result.report, CrossDocumentReport):
        return tuple(
            sorted(
                {
                    group.key.schema_hash
                    for group in report_result.report.groups
                    if group.key.schema_hash is not None
                }
            )
        )
    return ()


def _confidence_buckets(
    report_result: ReportWriteResult,
    config: ExtractorConfig,
) -> tuple[ReportConfidenceBucketSummary, ...]:
    data_points = (
        report_result.report.data_points
        if isinstance(report_result.report, ExtractionReport)
        else ()
    )
    bucket_configs = config.reporting.confidence_buckets
    summaries: list[ReportConfidenceBucketSummary] = []
    for index, bucket in enumerate(bucket_configs):
        upper_bound = 1.0 if index == 0 else bucket_configs[index - 1].minimum_confidence
        if index == 0:
            item_ids = tuple(
                data_point.data_point_id
                for data_point in data_points
                if data_point.confidence >= bucket.minimum_confidence
            )
        else:
            item_ids = tuple(
                data_point.data_point_id
                for data_point in data_points
                if bucket.minimum_confidence <= data_point.confidence < upper_bound
            )
        summaries.append(
            ReportConfidenceBucketSummary(
                bucket_name=bucket.bucket_name,
                item_ids=item_ids,
                count=len(item_ids),
                minimum_confidence=bucket.minimum_confidence,
                maximum_confidence=upper_bound,
            )
        )
    return tuple(summaries)


def _audit_digest_sha256(
    *,
    artifact: ReportArtifactRef,
    source_sha256s: tuple[str, ...],
    text_sha256s: tuple[str, ...],
    schema_hashes: tuple[str, ...],
    prompt_sha256s: tuple[str, ...],
    config_hash: str,
) -> str:
    return canonical_json_sha256(
        {
            "artifact": artifact,
            "source_sha256s": source_sha256s,
            "text_sha256s": text_sha256s,
            "schema_hashes": schema_hashes,
            "prompt_sha256s": prompt_sha256s,
            "config_sha256": config_hash,
        }
    )


def _manifest_signature_payload(manifest: SignedReportManifest) -> dict[str, Any]:
    payload = manifest.model_dump(mode="json")
    payload.pop("signature")
    return payload


def _render_manifest_json(manifest: SignedReportManifest) -> str:
    return json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _default_manifest_path(report_path: Path, suffix: str) -> Path:
    return report_path.with_name(f"{report_path.name}{suffix}")


__all__ = [
    "ReportSigningError",
    "canonical_json_bytes",
    "canonical_json_sha256",
    "config_sha256",
    "file_sha256",
    "sign_payload",
    "verify_signed_report_manifest",
    "verify_payload_signature",
    "write_signed_report_manifest",
]
