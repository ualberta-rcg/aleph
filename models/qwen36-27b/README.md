# Qwen3.6-27B

Qwen **Qwen3.6-27B** — a dense 27B model with a novel Gated-DeltaNet hybrid architecture.
Thinking mode (binary toggle), tool calling, and vision (image + video). TP2 across 2× L40S.

## What it does
- **Reasoning**: binary thinking via `enable_thinking`. `reasoning_effort: medium/high` → on;
  `none` → off (a real off, unlike gpt-oss).
- **Tool calling**: `qwen3_coder` parser.
- **Vision**: text + image (use base64-inline images; the cluster can't fetch external URLs).
- **Context**: 131,072.

## Thinking, through the gateway
Managed-thinking (effort + `enable_thinking` toggle):
- **ON** (`reasoning_effort: medium/high`, Anthropic `thinking: enabled`) → chain-of-thought in
  the **`reasoning`** field (OpenAI) / a **`thinking`** block (Anthropic).
- **OFF** (`reasoning_effort: none`) → no reasoning + `max_tokens` capped (2048).

## Call it
```bash
curl $GW/v1/chat/completions -d '{"model":"qwen36-27b","reasoning_effort":"high","max_tokens":16000,
  "messages":[{"role":"user","content":"Design a REST API for a todo app."}]}'
```

## Resources
- 2× L40S (whole devices), TP2, `vllm/vllm-openai:v0.20.2`, qwen3 + qwen3_coder parsers.
- Scale-to-zero: 15-min idle retention, wake-on-demand; cold start ~4–5 min.

## Source
[HuggingFace: Qwen/Qwen3.6-27B](https://huggingface.co/Qwen/Qwen3.6-27B)
