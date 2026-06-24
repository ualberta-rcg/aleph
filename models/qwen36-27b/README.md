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

## Testing
The 31-check vision+tools battery runs inside the gateway pod (first check wakes a scaled-to-zero model):
```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/qwen36-27b/test.py

# Or inside the gateway pod (no auth)
cat models/qwen36-27b/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```
Last run (2026-06-18): **29 PASS / 2 EXP / 0 FAIL** — image vision works, tools, managed thinking
ON/OFF/budget/stream, answer/finish_reason/model-echo/truncation assertions, Anthropic parity,
guardrails. (2 EXP = embed-via-Anthropic, bad-model.) Thinking-check `max_tokens` capped at 4096
to keep the verbose reasoner fast.

## Source
[HuggingFace: Qwen/Qwen3.6-27B](https://huggingface.co/Qwen/Qwen3.6-27B)
