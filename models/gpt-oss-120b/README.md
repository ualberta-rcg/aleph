# GPT-OSS 120B

OpenAI's open-weight **gpt-oss-120b** — a large MoE reasoning model (117B total / 5.1B active, 128 experts with 4 active, MXFP4). Text-only, configurable reasoning effort, native tool calling via the harmony format, near-parity with o4-mini on reasoning benchmarks. Served across 2× L40S.

## What it does
- **Reasoning** (always-on): effort `low` / `medium` / `high` via `reasoning_effort`. No fully-off mode — lowest is `low`.
- **Tool calling**: native harmony function calling; structured outputs.
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
curl $GW/v1/chat/completions -d '{"model":"gpt-oss-120b",
  "messages":[{"role":"user","content":"Design a REST API for a todo app."}],
  "reasoning_effort":"high","max_tokens":16000}'
# Anthropic — thinking on
curl $GW/v1/messages -d '{"model":"gpt-oss-120b","max_tokens":16000,
  "messages":[{"role":"user","content":"Design a REST API for a todo app."}],
  "thinking":{"type":"enabled","budget_tokens":8000}}'
```

## Resources
- 2× L40S (whole devices, no `gpumem`), **TP2**, `--disable-custom-all-reduce` (L40S PCIe topology, no NVLink P2P), `vllm/vllm-openai:v0.20.2`.
- ~200 tok/s; weights ~60 GB on PVC. Scale-to-zero: 15-min idle retention, wake-on-demand; cold start ~2–3 min.

## Source
[HuggingFace: openai/gpt-oss-120b](https://huggingface.co/openai/gpt-oss-120b) · Apache-2.0
