# Veritext Extractor

Research-grade, domain-agnostic document extraction engine optimized for extraction accuracy, auditable provenance, and invariant enforcement.

## Architecture

```text
document
  -> ingestion
  -> chunker
  -> planner
  -> executor
  -> critic
  -> verifier
  -> reconciler
  -> reporter
  -> audit store
```

## Current Status

Phases 0-18 are implemented through the CLI, evaluation scoring harness, hardened operational prompt pack, Anthropic/OpenAI/OpenAI-compatible LLM provider support, and local `.env` loading.

## Development

```bash
make test
make lint
make smoke
```

## LLM Provider

Configure the model in `config/default.yaml` or `config/local.yaml`. Supported providers are `anthropic`, `openai`, and `openai_compatible`; all LLM calls still go through `src/extractor/llm/client.py`. The canonical default uses Moonshot's OpenAI-compatible Kimi API.

```yaml
llm:
  provider: openai_compatible
  base_url: https://api.moonshot.ai/v1
  api_key_env: MOONSHOT_API_KEY
  model: kimi-k2.6
  stage_overrides:
    planner: {}
    executor: {}
    reconciler: {}
```

For local runs, create `.env` from `.env.example` and set `MOONSHOT_API_KEY`. Keep only secrets in `.env`; provider/model settings belong in YAML.

For Kimi models, Veritext sends Moonshot-compatible chat-completions requests with `max_tokens`, forced named function `tool_choice`, strict tool schemas, `parallel_tool_calls: false`, `extra_body: {"thinking": {"type": "disabled"}}`, no `temperature`, and no OpenAI-only `reasoning_effort`. Kimi thinking is disabled on these structured requests because Moonshot rejects specified `tool_choice` while thinking is enabled.

Recommended model presets:

```yaml
# Default Moonshot profile: all stages use Kimi K2.6.
llm:
  model: kimi-k2.6
  stage_overrides: {}
```

Moonshot enables Kimi thinking by default for models that support it. Veritext explicitly disables it for structured extraction calls to preserve the forced-tool invariant.

The default execution config keeps `max_stage_concurrency: 2` and `max_chunk_concurrency: 2` for Moonshot. If Moonshot returns `429 Too Many Requests` for organization concurrency, stop other runs or lower both values to `1` in `config/local.yaml`.

To change only one stage, edit `llm.stage_overrides.<stage>.model`, where `<stage>` is one of `planner`, `executor`, `critic`, `verifier`, or `reconciler`.

## Evaluations

Score a completed extraction report against a source-backed fixture:

```bash
python3 -m extractor.evals evals/fixtures/minimal_financial_update/expected.json evals/fixtures/minimal_financial_update/report.example.json
```

The included fixtures cover minimal financial update, contract obligation, policy control, and a mixed distractor example.

## Prompt Pack

The active prompt pack lives under `prompts/`. Each prompt keeps the required contract sections and instructs the model to use forced tool output, approved schema names, exact source spans, explicit rejection behavior, stage-specific examples, and adversarial checks.

## Accuracy Contract

The project will enforce the required invariants I1-I9 in code and tests as the corresponding stages are implemented. Runtime tuning values will live in configuration only.
