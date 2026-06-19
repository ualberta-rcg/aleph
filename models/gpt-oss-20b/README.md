# GPT-OSS 20B

OpenAI's open-weight **gpt-oss-20b** — a lightweight MoE reasoning model (21B total / 3.6B active, MXFP4). Text-only, configurable reasoning effort, native tool calling via the harmony format. Served on a single L40S vGPU slice.

## What it does
- **Reasoning** (always-on): effort `low` / `medium` / `high` via `reasoning_effort`. No fully-off mode — lowest is `low`.
- **Tool calling**: native harmony function calling.
- **Context**: 128K native, served at 131,072.
- **Text only** — images are rejected with `400 vision_unsupported`.

## Thinking, through the gateway
This is a **managed-thinking** model:
- **ON** (`reasoning_effort: medium/high`, or Anthropic `thinking: enabled`) → chain-of-thought is returned in the **`reasoning`** field (OpenAI) / a **`thinking`** content block (Anthropic), including in streaming.
- **OFF** (`reasoning_effort: none` / Anthropic `thinking: disabled`) → reasoning is stripped **and** `max_tokens` is capped to 2048, so the client sees only a direct answer.
- A caller `thinking_token_budget` fakes a token cap (gpt-oss has no native budget) by limiting `max_tokens`.

## Call it
```bash
# OpenAI — reasoning on
curl $GW/v1/chat/completions -d '{"model":"gpt-oss-20b",
  "messages":[{"role":"user","content":"Explain RC circuits."}],
  "reasoning_effort":"high","max_tokens":16000}'
# Anthropic — thinking on
curl $GW/v1/messages -d '{"model":"gpt-oss-20b","max_tokens":16000,
  "messages":[{"role":"user","content":"Explain RC circuits."}],
  "thinking":{"type":"enabled","budget_tokens":8000}}'
```

## Resources
- 1× L40S vGPU slice (~24 GB), TP1, `vllm/vllm-openai:v0.20.2`.
- Scale-to-zero: 15-min idle retention, wake-on-demand; cold start ~2 min.

## Testing
The 34-check battery runs inside the gateway pod (the first check wakes a scaled-to-zero model):
```bash
cat models/gpt-oss-20b/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```
Last run (2026-06-18): **31 PASS / 3 EXP / 0 FAIL** — managed thinking ON/OFF + token-budget + streaming reasoning, tools, Anthropic parity, truncation, meta-tasks, guardrails.

## Source
[HuggingFace: openai/gpt-oss-20b](https://huggingface.co/openai/gpt-oss-20b) · Apache-2.0
