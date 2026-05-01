#!/usr/bin/env bash
# Convenience wrapper around scripts/debug_planner_only.py for the medium
# research fixture. Runs ingest + chunk + planner only, stopping before the
# executor so the operator can review classify / propose / critique / strategy
# / budget outputs.
#
# Usage:
#   ./scripts/debug_medium_research.sh                       # all 5 planner sub-stages, persist plan
#   ./scripts/debug_medium_research.sh --stop-after propose  # stop after propose_schema
#   RUN_ID=my-id ./scripts/debug_medium_research.sh          # pick the run id
#
# After the planner looks correct, continue from the executor with the SAME run id:
#   PYTHONPATH=src python3 -m extractor.cli \
#     evals/fixtures/medium_research_brief/source.md \
#     --output outputs/<run-id>.json --run-id <run-id> --resume

set -euo pipefail
cd "$(dirname "$0")/.."

RUN_ID="${RUN_ID:-medium-research-debug-$(date +%Y%m%d-%H%M%S)}"
SOURCE="evals/fixtures/medium_research_brief/source.md"

PYTHONPATH=src python3 scripts/debug_planner_only.py \
  "${SOURCE}" \
  --run-id "${RUN_ID}" \
  "$@"
