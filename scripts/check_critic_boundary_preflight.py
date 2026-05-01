"""Local preflight for critic verdict boundary normalization.

This script makes no API calls. It verifies that the current Python import path
uses the repo-local payload normalizer and that critic verdicts with an invalid
non-null correction on a reject decision are normalized before strict Pydantic
validation.
"""

from __future__ import annotations

import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from extractor.critic.models import CriticBatchVerdicts
from extractor.llm import payloads


def main() -> int:
    print(f"payloads_path={payloads.__file__}")

    payload = {
        "verdicts": [
            {
                "id": "e0246968cc94",
                "decision": "reject",
                "code": "critic_rejected",
                "evidence": "bad",
                "correction": {"span_start_char": 20, "span_text": "18%"},
            }
        ]
    }
    verdict = CriticBatchVerdicts.model_validate(payload).verdicts[0]

    if verdict.decision != "reject":
        raise AssertionError(f"unexpected decision: {verdict.decision!r}")
    if verdict.code != "critic_rejected":
        raise AssertionError(f"unexpected code: {verdict.code!r}")
    if verdict.correction is not None:
        raise AssertionError(f"correction was not stripped: {verdict.correction!r}")

    print("critic boundary preflight passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
