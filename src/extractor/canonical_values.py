from __future__ import annotations

import re
import unicodedata

from extractor.contracts import CanonicalValueKey, DataPoint, LensCandidate
from extractor.contracts.dedup import CanonicalValueSource
from extractor.contracts.normalization import NormalizationStatus, ValueKind


def canonical_value_key_for_candidate(candidate: LensCandidate) -> CanonicalValueKey:
    return canonical_value_key(
        value=candidate.value,
        value_verbatim=candidate.value_verbatim,
        value_canonical=candidate.value_canonical,
        value_kind=candidate.value_kind,
        normalization_status=candidate.normalization_status,
        policy_id=candidate.normalization_policy_id,
        policy_version=candidate.normalization_policy_version,
    )


def canonical_value_key_for_data_point(data_point: DataPoint) -> CanonicalValueKey:
    return canonical_value_key(
        value=data_point.value,
        value_verbatim=data_point.value_verbatim,
        value_canonical=data_point.value_canonical,
        value_kind=data_point.value_kind,
        normalization_status=data_point.normalization_status,
        policy_id=data_point.normalization_policy_id,
        policy_version=data_point.normalization_policy_version,
    )


def canonical_value_key(
    *,
    value: str,
    value_verbatim: str | None,
    value_canonical: str | None,
    value_kind: ValueKind,
    normalization_status: NormalizationStatus,
    policy_id: str | None,
    policy_version: str | None,
) -> CanonicalValueKey:
    raw_value, source = _canonical_key_source(
        value=value,
        value_verbatim=value_verbatim,
        value_canonical=value_canonical,
        normalization_status=normalization_status,
    )
    return CanonicalValueKey(
        kind=value_kind,
        key=_normalize_key_text(raw_value),
        source=source,
        policy_id=policy_id,
        policy_version=policy_version,
    )


def canonical_value_key_identity(canonical_key: CanonicalValueKey) -> tuple[object, ...]:
    return (
        canonical_key.kind,
        canonical_key.key,
        canonical_key.source,
        canonical_key.policy_id,
        canonical_key.policy_version,
    )


def _canonical_key_source(
    *,
    value: str,
    value_verbatim: str | None,
    value_canonical: str | None,
    normalization_status: NormalizationStatus,
) -> tuple[str, CanonicalValueSource]:
    if normalization_status == "canonicalized":
        return value_canonical or value, "value_canonical"
    if normalization_status == "verbatim_only":
        return value_verbatim or value, "value_verbatim"
    return value, "value"


def _normalize_key_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value)
    text = text.translate(
        str.maketrans(
            {
                "\u2010": "-",
                "\u2011": "-",
                "\u2012": "-",
                "\u2013": "-",
                "\u2014": "-",
                "\u2015": "-",
                "\u2212": "-",
                "\u2018": "'",
                "\u2019": "'",
                "\u201c": '"',
                "\u201d": '"',
            }
        )
    )
    text = text.strip().strip("\"'`.,;:()[]{}<>")
    normalized = re.sub(r"\s+", " ", text).casefold()
    return normalized or value


__all__ = [
    "canonical_value_key",
    "canonical_value_key_for_candidate",
    "canonical_value_key_for_data_point",
    "canonical_value_key_identity",
]
