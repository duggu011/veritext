# Output scope policy

Veritext's default product behavior is **comprehensive source-backed
extraction**: emit every material fact the planner approves and downstream
stages can preserve with audited provenance.

This policy matters because an evaluation fixture may intentionally expect a
smaller target set than a general document user would want. In that case, a
source-backed extra output is an eval false positive, but not automatically a
product defect.

## Current default

- Extract all material source-backed facts in the document.
- Preserve the exact source span and value semantics through every stage.
- Reject candidates that fail provenance, approved-schema, or correction
  invariants.
- Do not drop valid facts only because a benchmark case omitted them.

## Task-scoped extraction

Task-scoped extraction is a future mode, not the current default. It should be
used when an operator supplies a target schema or explicit extraction question.
In that mode, precision is measured against the requested scope rather than
against every source-backed fact in the document.

## Hybrid reporting

A future reporting layer may classify outputs as core, supporting, or
contextual. That would let the pipeline remain comprehensive while allowing
applications and evals to focus on a narrower subset without deleting auditably
correct facts.

## Quality implications

- Fix provenance, correction drift, and value normalization regardless of
  scope.
- Treat fixture-only false positives carefully: first ask whether the value is
  source-backed and material.
- Prefer general role and field semantics over fixture-specific whitelists.
- Do not hardcode document names, companies, people, or assets to improve a
  single benchmark.
