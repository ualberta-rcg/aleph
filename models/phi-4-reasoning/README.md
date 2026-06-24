# Phi-4-Reasoning

Microsoft **Phi-4-reasoning** — a 14B dense decoder-only model (SFT + RL on chain-of-thought) tuned
for math, science, and code reasoning. Text-only, **no tool calling**. Served on a single whole L40S.

## What it does
- **Reasoning** (always-on, budget-controlled): `reasoning_effort` maps to a `thinking_token_budget`
  via an effort map — `none`=512, `low`=1024, `medium`=4096, `high`=12288, `xhigh`=24576, `max`=off.
- **No tools / no vision**: both rejected with `400` (`tools_unsupported` / `vision_unsupported`).
- **Context**: 32K native, served at 32,768; max completion 16,000.
- Native output is `Thought` inside `redacted_thinking` tags, then `Solution` (deepseek_r1 parser).

## Thinking, through the gateway
Managed-thinking **budget** mode (the gateway owns the budget, not the model's effort flag):
- **ON** (`reasoning_effort: medium/high/…`) → chain-of-thought in the **`reasoning`** field (OpenAI) /
  a **`thinking`** block (Anthropic). Higher effort = larger budget = deeper reasoning.
- **OFF** (`reasoning_effort: none`) → budget **reduced to 512** (not 0 — budget 0 is mishandled per
  vLLM#18141, burns tokens/empty content) + reasoning stripped + `max_tokens` capped to 4096.
- `max_tokens` is **one shared budget for Thought + Solution** — give it adequate room or the CoT
  exhausts it before the answer appears (HF recommends up to 32768 for hard problems).

## Call it
```bash
# OpenAI — reasoning on (high effort)
curl $GW/v1/chat/completions -d '{"model":"phi-4-reasoning",
  "messages":[{"role":"user","content":"Prove sqrt(2) is irrational."}],
  "reasoning_effort":"high","max_tokens":16000}'
```

## Resources
- 1× L40S (**whole device, no `gpumem`** — HAMi vGPU mode breaks the deepseek_r1 reasoning split), TP1,
  `vllm/vllm-openai:v0.20.2`, `--reasoning-parser deepseek_r1`.
- Scale-to-zero: 15-min idle retention, wake-on-demand; cold start ~3–5 min.

## Testing
The 31-check budget battery runs inside the gateway pod (first check wakes a scaled-to-zero model):
```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/phi-4-reasoning/test.py

# Or inside the gateway pod (no auth)
cat models/phi-4-reasoning/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```
Last run (2026-06-18): **26 PASS / 5 EXP / 0 FAIL** — managed thinking ON (budget) / OFF (strip+cap),
streaming reasoning, stop/system, tools-rejected + vision-rejected guards, Anthropic parity,
catalog. (5 EXP = tools-rejected, vision-rejected, embed-via-Anthropic, ANT-tools-rejected, bad-model.)

## Source
[HuggingFace: microsoft/Phi-4-reasoning](https://huggingface.co/microsoft/Phi-4-reasoning) · MIT
