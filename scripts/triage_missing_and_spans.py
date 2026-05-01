"""Read-only triage of an extraction run against an evaluation case.

Given a run id, the eval case file, and the report JSON, classify each
missing-expected item into one of:

  (a) executor never produced a candidate matching (category, field_name,
      normalized value)
  (b) executor produced one but rejected it before dedup
  (c) dedup merged it into a survivor that itself was later rejected
  (d) critic rejected it
  (e) verifier rejected it
  (f) reconciler rejected it
  (g) candidate survived but did not surface as a data point (unexpected
      pipeline state worth flagging)
  (h) candidate survived AND a data point exists, but the eval still flagged
      missing (value/category normalization mismatch worth review)

Then list every true-positive whose source span differs from the expected
case-file span, side by side.

No LLM calls. No pipeline imports beyond evals/scoring (for the matcher) and
reporter (to load the report). Reads the audit sqlite directly.

Usage::

    PYTHONPATH=src python3 scripts/triage_missing_and_spans.py \\
        --run-id medium-research-debug-20260501-185509 \\
        --case evals/fixtures/medium_research_brief/case.json \\
        --report outputs/medium-research-debug-20260501-185509.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from extractor.evals.scoring import (
    evaluate_report_file,
    load_evaluation_case,
    load_extraction_report,
)


# Match the eval scoring normalization exactly so categorisation lines up.
def _normalize(value: str) -> str:
    return " ".join(value.split()).casefold()


def _key(category: str, field_name: str, value: str) -> tuple[str, str, str]:
    return _normalize(category), _normalize(field_name), _normalize(value)


@dataclass
class CandidateRow:
    candidate_id: str
    chunk_id: str
    category: str
    field_name: str
    value: str
    payload: dict
    rejections: list[dict] = field(default_factory=list)
    critic_reports: list[dict] = field(default_factory=list)
    verifier_reports: list[dict] = field(default_factory=list)
    surviving_data_point_id: str | None = None
    merged_into: str | None = None  # populated for dedup rejections


def _load_run(audit_path: Path, run_id: str) -> tuple[
    dict[str, CandidateRow],  # candidates by id
    dict[tuple[str, str, str], list[CandidateRow]],  # by normalized key
    dict[str, dict],  # data_points by id
    dict[str, str],  # candidate_id -> data_point_id
]:
    conn = sqlite3.connect(f"file:{audit_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        candidates: dict[str, CandidateRow] = {}
        by_key: dict[tuple[str, str, str], list[CandidateRow]] = defaultdict(list)
        for row in conn.execute(
            "SELECT candidate_id, chunk_id, category, field_name, payload_json"
            " FROM lens_candidates WHERE run_id = ?",
            (run_id,),
        ):
            payload = json.loads(row["payload_json"])
            value = payload.get("value", "")
            cand = CandidateRow(
                candidate_id=row["candidate_id"],
                chunk_id=row["chunk_id"],
                category=row["category"],
                field_name=row["field_name"],
                value=value,
                payload=payload,
            )
            candidates[cand.candidate_id] = cand
            by_key[_key(cand.category, cand.field_name, cand.value)].append(cand)

        for row in conn.execute(
            "SELECT candidate_id, stage, payload_json FROM candidate_rejections"
            " WHERE run_id = ?",
            (run_id,),
        ):
            cand = candidates.get(row["candidate_id"])
            if cand is None:
                continue
            payload = json.loads(row["payload_json"])
            payload["_stage"] = row["stage"]
            cand.rejections.append(payload)
            if row["stage"] == "dedup":
                for reason in payload.get("reasons", []):
                    msg = reason.get("message", "")
                    if msg.startswith("merged_into:"):
                        cand.merged_into = msg.split(":", 1)[1].strip()
                        break

        for row in conn.execute(
            "SELECT candidate_id, payload_json FROM critic_reports WHERE run_id = ?",
            (run_id,),
        ):
            cand = candidates.get(row["candidate_id"])
            if cand is None:
                continue
            cand.critic_reports.append(json.loads(row["payload_json"]))

        for row in conn.execute(
            "SELECT candidate_id, payload_json FROM verifier_reports WHERE run_id = ?",
            (run_id,),
        ):
            cand = candidates.get(row["candidate_id"])
            if cand is None:
                continue
            cand.verifier_reports.append(json.loads(row["payload_json"]))

        data_points: dict[str, dict] = {}
        cand_to_dp: dict[str, str] = {}
        for row in conn.execute(
            "SELECT data_point_id, payload_json FROM data_points WHERE run_id = ?",
            (run_id,),
        ):
            payload = json.loads(row["payload_json"])
            data_points[row["data_point_id"]] = payload
            for cid in payload.get("contributing_candidate_ids", []):
                cand_to_dp[cid] = row["data_point_id"]
                if cid in candidates:
                    candidates[cid].surviving_data_point_id = row["data_point_id"]
        return candidates, by_key, data_points, cand_to_dp
    finally:
        conn.close()


def _classify_candidate_fate(
    cand: CandidateRow, candidates: dict[str, CandidateRow]
) -> tuple[str, list[str]]:
    """Return (bucket, evidence_lines) for a single candidate.

    bucket is one of: data_point, executor_rejected, dedup_merged_to_*,
    critic_rejected, verifier_rejected, reconciler_rejected, no_outcome.
    """
    if cand.surviving_data_point_id:
        return (
            "data_point",
            [f"surfaced as {cand.surviving_data_point_id}"],
        )

    stages = {r["_stage"] for r in cand.rejections}
    lines: list[str] = []

    if "executor" in stages:
        for r in cand.rejections:
            if r["_stage"] == "executor":
                for reason in r.get("reasons", []):
                    lines.append(
                        f"[executor] {reason.get('code')}: {reason.get('message')}"
                    )
        return "executor_rejected", lines

    if "critic" in stages:
        for r in cand.rejections:
            if r["_stage"] == "critic":
                for reason in r.get("reasons", []):
                    lines.append(
                        f"[critic] {reason.get('code')}: {reason.get('message')}"
                    )
        for cr in cand.critic_reports:
            if not cr.get("accepted", True):
                for issue in cr.get("issues", []):
                    lines.append(
                        f"[critic.report] {issue.get('severity')} {issue.get('code')}: {issue.get('message')}"
                    )
        return "critic_rejected", lines

    if "verifier" in stages:
        for r in cand.rejections:
            if r["_stage"] == "verifier":
                for reason in r.get("reasons", []):
                    lines.append(
                        f"[verifier] {reason.get('code')}: {reason.get('message')}"
                    )
        for vr in cand.verifier_reports:
            if not vr.get("accepted", True):
                for reason in vr.get("rejection_reasons", []):
                    lines.append(
                        f"[verifier.report] {reason.get('code')}: {reason.get('message')}"
                    )
        return "verifier_rejected", lines

    if "reconciler" in stages:
        for r in cand.rejections:
            if r["_stage"] == "reconciler":
                for reason in r.get("reasons", []):
                    lines.append(
                        f"[reconciler] {reason.get('code')}: {reason.get('message')}"
                    )
        return "reconciler_rejected", lines

    if "dedup" in stages and cand.merged_into:
        survivor = candidates.get(cand.merged_into)
        if survivor is None:
            return (
                "dedup_merged_unknown",
                [f"merged into {cand.merged_into} (not in candidate table)"],
            )
        sub_bucket, sub_lines = _classify_candidate_fate(survivor, candidates)
        prefix = f"merged into {cand.merged_into} -> {sub_bucket}"
        return (
            f"dedup_then_{sub_bucket}",
            [prefix, *[f"    {ln}" for ln in sub_lines]],
        )

    return "no_outcome", ["no rejection rows and no data point — investigate"]


def _format_expected(exp: dict) -> list[str]:
    return [
        f"  category   : {exp['category']}",
        f"  field_name : {exp['field_name']}",
        f"  value      : {exp['value']!r}",
        f"  span       : [{exp['start_char']}, {exp['end_char']})  bytes [{exp['start_byte']}, {exp['end_byte']})",
        f"  source_text: {exp['source_text']!r}",
    ]


def _format_candidate(cand: CandidateRow) -> list[str]:
    span = cand.payload.get("source_span", {}) or {}
    return [
        f"  candidate  : {cand.candidate_id}",
        f"  category   : {cand.category}",
        f"  field_name : {cand.field_name}",
        f"  value      : {cand.value!r}",
        f"  span       : [{span.get('start_char')}, {span.get('end_char')})  bytes [{span.get('start_byte')}, {span.get('end_byte')})",
        f"  span.text  : {span.get('text')!r}",
        f"  lens       : {cand.payload.get('lens')}",
        f"  confidence : {cand.payload.get('confidence')}",
    ]


def _near_match_candidates(
    exp: dict,
    by_key: dict[tuple[str, str, str], list[CandidateRow]],
) -> list[CandidateRow]:
    """Find candidates that share category+field_name but not value."""
    cat = _normalize(exp["category"])
    field = _normalize(exp["field_name"])
    matches: list[CandidateRow] = []
    for (c, f, _v), cands in by_key.items():
        if c == cat and f == field:
            matches.extend(cands)
    return matches


def triage_missing(
    expected_by_id: dict[str, dict],
    missing_ids: list[str],
    candidates: dict[str, CandidateRow],
    by_key: dict[tuple[str, str, str], list[CandidateRow]],
) -> list[str]:
    out: list[str] = []
    bucket_counts: dict[str, int] = defaultdict(int)

    for exp_id in missing_ids:
        exp = expected_by_id[exp_id]
        out.append("")
        out.append(f"### {exp_id}")
        out.extend(_format_expected(exp))

        key = _key(exp["category"], exp["field_name"], exp["value"])
        exact_cands = by_key.get(key, [])

        if not exact_cands:
            bucket_counts["(a) no_candidate"] += 1
            out.append("  fate       : (a) executor never produced a candidate with matching key")
            near = _near_match_candidates(exp, by_key)
            if near:
                out.append(f"  near-misses (same category+field, {len(near)} cand(s)):")
                for nc in near[:6]:
                    out.append(f"    - {nc.candidate_id}  value={nc.value!r}")
                if len(near) > 6:
                    out.append(f"    ... and {len(near) - 6} more")
            else:
                out.append("  near-misses: none (executor produced nothing in this category+field)")
            continue

        out.append(
            f"  fate       : candidate(s) exist with matching key (count={len(exact_cands)})"
        )
        per_bucket: list[str] = []
        for cand in exact_cands:
            sub_bucket, sub_lines = _classify_candidate_fate(cand, candidates)
            per_bucket.append(sub_bucket)
            out.append(f"  - {cand.candidate_id} -> {sub_bucket}")
            for ln in _format_candidate(cand)[1:]:  # skip duplicate id line
                out.append(f"    {ln}")
            for ln in sub_lines:
                out.append(f"    {ln}")
        # Headline bucket = first non-data_point fate (data_point would mean it
        # surfaced and the eval still missed it, which is bucket (h)).
        if any(b == "data_point" for b in per_bucket):
            bucket_counts["(h) surfaced_but_not_matched"] += 1
        elif any(b.startswith("critic") for b in per_bucket):
            bucket_counts["(d) critic_rejected"] += 1
        elif any(b.startswith("verifier") for b in per_bucket):
            bucket_counts["(e) verifier_rejected"] += 1
        elif any(b == "executor_rejected" for b in per_bucket):
            bucket_counts["(b) executor_rejected"] += 1
        elif any(b.startswith("dedup_then_") for b in per_bucket):
            bucket_counts["(c) dedup_merged_then_lost"] += 1
        elif any(b.startswith("reconciler") for b in per_bucket):
            bucket_counts["(f) reconciler_rejected"] += 1
        else:
            bucket_counts["(g) no_outcome"] += 1

    # Prepend summary
    summary = ["", "## Missing-expected bucket counts", ""]
    for k in sorted(bucket_counts):
        summary.append(f"- {k}: {bucket_counts[k]}")
    summary.append(f"- total: {len(missing_ids)}")
    return summary + out


def triage_wrong_spans(
    expected_by_id: dict[str, dict],
    matches: list,
    data_points: dict[str, dict],
    source_text: str,
) -> list[str]:
    out: list[str] = ["", "## Provenance mismatches (TPs with wrong span)", ""]
    rows = [m for m in matches if not m.exact_provenance]
    out.append(f"count: {len(rows)}")
    for m in rows:
        exp = expected_by_id[m.expected_id]
        dp = data_points[m.data_point_id]
        span = dp.get("source_span", {}) or {}
        out.append("")
        out.append(f"### {m.expected_id}  vs  {m.data_point_id}")
        out.append(f"  category   : {exp['category']} / {exp['field_name']} = {exp['value']!r}")
        out.append(
            f"  expected   : [{exp['start_char']}, {exp['end_char']}) bytes "
            f"[{exp['start_byte']}, {exp['end_byte']})"
        )
        out.append(f"               text={exp['source_text']!r}")
        out.append(
            f"  actual     : [{span.get('start_char')}, {span.get('end_char')}) bytes "
            f"[{span.get('start_byte')}, {span.get('end_byte')})"
        )
        out.append(f"               text={span.get('text')!r}")
        # Diagnose the difference shape.
        try:
            es, ee = exp["start_char"], exp["end_char"]
            asx, ae = span["start_char"], span["end_char"]
            if asx >= es and ae <= ee:
                shape = "narrower (subset of expected)"
            elif asx <= es and ae >= ee:
                shape = "wider (superset of expected)"
            elif ae <= es or asx >= ee:
                shape = "disjoint"
            else:
                shape = "overlapping (shifted)"
            out.append(f"  shape      : {shape}")
        except (KeyError, TypeError):
            pass
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--case", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--audit", default=Path(".veritext/audit.sqlite3"), type=Path)
    parser.add_argument("--out", type=Path, help="optional path to write the markdown report")
    args = parser.parse_args(argv)

    if not args.audit.exists():
        parser.error(f"audit DB not found: {args.audit}")
    if not args.case.exists():
        parser.error(f"case file not found: {args.case}")
    if not args.report.exists():
        parser.error(f"report file not found: {args.report}")

    case = load_evaluation_case(args.case)
    report = load_extraction_report(args.report)
    if report.run_id != args.run_id:
        print(
            f"warning: report run_id={report.run_id!r} != --run-id={args.run_id!r}",
            file=sys.stderr,
        )
    result = evaluate_report_file(args.case, args.report)

    expected_by_id = {ed.expected_id: ed.model_dump() for ed in case.expected_data_points}

    candidates, by_key, data_points, _cand_to_dp = _load_run(args.audit, args.run_id)

    lines: list[str] = []
    lines.append(f"# Triage report — run {args.run_id}")
    lines.append("")
    lines.append(f"- case: {args.case}")
    lines.append(f"- report: {args.report}")
    lines.append(f"- audit: {args.audit}")
    lines.append(f"- expected: {result.metrics.expected_count}")
    lines.append(f"- actual: {result.metrics.actual_count}")
    lines.append(
        f"- TP: {result.metrics.true_positives}  "
        f"(exact_prov={result.metrics.exact_provenance_matches})"
    )
    lines.append(
        f"- FN: {result.metrics.false_negatives}  FP: {result.metrics.false_positives}"
    )
    lines.append(
        f"- precision={result.metrics.precision:.3f} recall={result.metrics.recall:.3f} "
        f"f1={result.metrics.f1:.3f} provenance_recall={result.metrics.provenance_recall:.3f}"
    )
    lines.append(f"- candidates in audit: {len(candidates)}")
    lines.append(f"- data points in audit: {len(data_points)}")

    lines.append("")
    lines.append("## Missing expected items")
    lines.append("")
    lines.append(
        "Buckets: (a) executor never produced  (b) executor rejected  "
        "(c) dedup merged then lost  (d) critic rejected  (e) verifier rejected  "
        "(f) reconciler rejected  (g) no outcome  (h) surfaced but eval did not match"
    )
    lines.extend(
        triage_missing(
            expected_by_id,
            list(result.missing_expected_ids),
            candidates,
            by_key,
        )
    )

    lines.extend(
        triage_wrong_spans(
            expected_by_id,
            list(result.matches),
            data_points,
            case.source_text,
        )
    )

    output = "\n".join(lines) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
