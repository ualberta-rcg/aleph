# Gemma 4 26B A4B

Google **Gemma 4 26B A4B** — a multimodal MoE (25.2B total / 3.8B active, FP8). Text + image
input, configurable thinking, native tool calling. Served on a single L40S.

## What it does
- **Vision**: text + image (up to 16 images/prompt). Use base64-inline images (the cluster
  can't fetch external URLs).
- **Reasoning**: binary thinking via `enable_thinking` (toggle). `reasoning_effort: medium/high`
  → on; `none` → off.
- **Tool calling**: native gemma4 function calling.
- **Context**: 256K native, deployed at 131,072.

## Thinking, through the gateway
Managed-thinking (**toggle** mode):
- **ON** (`reasoning_effort: medium/high`, Anthropic `thinking: enabled`) → chain-of-thought in
  the **`reasoning`** field (OpenAI) / a **`thinking`** block (Anthropic).
- **OFF** (`reasoning_effort: none`) → no reasoning + `max_tokens` capped (2048).
- gemma-4 activates thinking via `chat_template_kwargs.enable_thinking`, **not** `reasoning_effort`
  directly — the gateway maps effort → `enable_thinking` (sending raw `reasoning_effort` yields no
  thinking trace; that was the original bug).

## Call it
```bash
# OpenAI — vision + reasoning
curl $GW/v1/chat/completions -d '{"model":"gemma-4-26b-a4b","reasoning_effort":"high","max_tokens":16000,
  "messages":[{"role":"user","content":[
    {"type":"text","text":"What is in this image?"},
    {"type":"image_url","image_url":{"url":"data:image/png;base64,..."}}]}]}'
# Anthropic — thinking on
curl $GW/v1/messages -d '{"model":"gemma-4-26b-a4b","max_tokens":16000,
  "messages":[{"role":"user","content":"Design a REST API for a todo app."}],
  "thinking":{"type":"enabled","budget_tokens":8000}}'
```

## Resources
- 1× L40S (FP8, ~25 GB weights), TP1, `vllm/vllm-openai:v0.20.2`, gemma4 reasoning + tool parsers.
- Scale-to-zero: 15-min idle retention, wake-on-demand; cold start ~3 min.

## Testing
The 33-check vision battery runs inside the gateway pod (first check wakes a scaled-to-zero model):
```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/gemma-4-26b-a4b/test.py

# Or inside the gateway pod (no auth)
cat models/gemma-4-26b-a4b/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```
Last run (2026-06-18): **31 PASS / 2 EXP / 0 FAIL** — image vision works, tools (gemma4 parser),
managed thinking ON/OFF/budget/stream, answer/finish_reason/model-echo/truncation assertions,
Anthropic parity, guardrails.

## Source
[HuggingFace: google/gemma-4-26B-A4B-it](https://huggingface.co/google/gemma-4-26B-A4B-it) · Apache-2.0
