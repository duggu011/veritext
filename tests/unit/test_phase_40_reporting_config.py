from pathlib import Path

import pytest
from pydantic import ValidationError

from extractor.config import (
    ConfidenceBucketConfig,
    ReportSigningConfig,
    ReportingConfig,
    load_config,
)


ROOT = Path(__file__).resolve().parents[2]


def write_default_config(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "default.yaml").write_text(
        (ROOT / "config" / "default.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )


def test_default_reporting_config_file_loads() -> None:
    config = load_config(env={}, include_local=False)

    assert config.reporting.signing.enabled is False
    assert config.reporting.signing.algorithm == "hmac-sha256"
    assert config.reporting.signing.key_id == "local-dev"
    assert config.reporting.signing.key_env == "REPORT_SIGNING_KEY"
    assert config.reporting.signing.manifest_suffix == ".manifest.json"
    assert tuple(bucket.bucket_name for bucket in config.reporting.confidence_buckets) == (
        "verified",
        "probable",
        "tentative",
    )
    assert tuple(bucket.minimum_confidence for bucket in config.reporting.confidence_buckets) == (
        0.85,
        0.65,
        0.0,
    )


def test_reporting_settings_support_env_overrides(tmp_path: Path) -> None:
    write_default_config(tmp_path)

    config = load_config(
        config_dir=tmp_path,
        env={
            "VERITEXT_REPORTING__SIGNING__ENABLED": "true",
            "VERITEXT_REPORTING__SIGNING__KEY_ID": "phase-40-key",
            "VERITEXT_REPORTING__SIGNING__KEY_ENV": "VERITEXT_PHASE40_KEY",
            "VERITEXT_REPORTING__SIGNING__MANIFEST_SUFFIX": ".sig.json",
        },
    )

    assert config.reporting.signing.enabled is True
    assert config.reporting.signing.key_id == "phase-40-key"
    assert config.reporting.signing.key_env == "VERITEXT_PHASE40_KEY"
    assert config.reporting.signing.manifest_suffix == ".sig.json"


def test_reporting_config_rejects_unknown_keys_and_invalid_thresholds() -> None:
    with pytest.raises(ValidationError):
        ReportingConfig(
            signing=ReportSigningConfig(),
            confidence_buckets=(
                ConfidenceBucketConfig(bucket_name="verified", minimum_confidence=0.85),
                ConfidenceBucketConfig(bucket_name="probable", minimum_confidence=0.65),
                ConfidenceBucketConfig(bucket_name="tentative", minimum_confidence=0.0),
            ),
            unexpected=True,
        )

    with pytest.raises(ValidationError):
        ReportSigningConfig(algorithm="ed25519")

    with pytest.raises(ValidationError):
        ReportSigningConfig(enabled="false")

    with pytest.raises(ValidationError, match="verified"):
        ReportingConfig(
            signing=ReportSigningConfig(),
            confidence_buckets=(
                ConfidenceBucketConfig(bucket_name="probable", minimum_confidence=0.65),
                ConfidenceBucketConfig(bucket_name="verified", minimum_confidence=0.85),
                ConfidenceBucketConfig(bucket_name="tentative", minimum_confidence=0.0),
            ),
        )

    with pytest.raises(ValidationError, match="descending"):
        ReportingConfig(
            signing=ReportSigningConfig(),
            confidence_buckets=(
                ConfidenceBucketConfig(bucket_name="verified", minimum_confidence=0.85),
                ConfidenceBucketConfig(bucket_name="probable", minimum_confidence=0.9),
                ConfidenceBucketConfig(bucket_name="tentative", minimum_confidence=0.0),
            ),
        )
