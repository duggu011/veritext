#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${MOONSHOT_API_KEY:-}" ]]; then
  echo "MOONSHOT_API_KEY is not set" >&2
  exit 1
fi

payload_file="$(mktemp)"
trap 'rm -f "$payload_file"' EXIT

cat >"$payload_file" <<'JSON'
{
  "model": "kimi-k2.6",
  "max_tokens": 2048,
  "thinking": {"type": "disabled"},
  "messages": [
    {
      "role": "system",
      "content": "You extract entity candidates from one chunk. You must call the required tool exactly once. Do not answer in prose. Return candidates only when source_text appears exactly in chunk.text. Offset rule: chunk.start_char is the absolute document character offset of chunk.text[0]. For each candidate: find source_text inside chunk.text, let chunk_relative_index be the zero-based character index where source_text begins in chunk.text, and return start_char = chunk.start_char + chunk_relative_index. Do not estimate start_char. Do not use byte offsets, token offsets, line offsets, or end offsets. Before returning, verify: chunk.text[start_char - chunk.start_char : start_char - chunk.start_char + len(source_text)] == source_text. Allowed candidate keys are exactly: category, field_name, value, source_text, start_char, confidence. Never output start_text, start, offset, start_offset, end_char, start_byte, or end_byte."
    },
    {
      "role": "user",
      "content": "{\"run_id\":\"offset-test-1\",\"lens\":\"entity\",\"plan\":{\"approved_categories\":[{\"name\":\"CorporateEvent\",\"fields\":[{\"name\":\"parties\",\"description\":\"Named organizations involved in the event.\"}]}]},\"chunk\":{\"chunk_id\":\"chunk-test-1\",\"doc_id\":\"doc-test-1\",\"start_char\":5000,\"end_char\":5091,\"text\":\"0123456789ABCDEFGHIJNorthwind Storage signed the agreement with Pacific Northern Utilities.\"}}"
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "extract_entity_candidates",
        "description": "Extract entity candidates from one chunk.",
        "strict": true,
        "parameters": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "candidates": {
              "type": "array",
              "items": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                  "category": {"type": "string"},
                  "field_name": {"type": "string"},
                  "value": {"type": "string"},
                  "source_text": {"type": "string"},
                  "start_char": {"type": "integer", "minimum": 0},
                  "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                },
                "required": [
                  "category",
                  "field_name",
                  "value",
                  "source_text",
                  "start_char",
                  "confidence"
                ]
              }
            }
          },
          "required": ["candidates"]
        }
      }
    }
  ],
  "tool_choice": {
    "type": "function",
    "function": {"name": "extract_entity_candidates"}
  },
  "parallel_tool_calls": false
}
JSON

curl https://api.moonshot.ai/v1/chat/completions \
  -H "Authorization: Bearer ${MOONSHOT_API_KEY}" \
  -H "Content-Type: application/json" \
  --data-binary @"$payload_file"

echo
echo "Expected start_char values: Northwind Storage=5020, Pacific Northern Utilities=5064"
