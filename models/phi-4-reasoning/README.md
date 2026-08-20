# Phi-4-Reasoning

Microsoft **Phi-4-reasoning** — a 14B dense decoder-only model (SFT + RL on chain-of-thought) tuned
for math, science, and code reasoning. Text-only, **no tool calling**. Served on a single whole L40S.

## What it does
- **Reasoning** (always thinks; budget-controlled): `reasoning_effort` maps to a `thinking_token_budget`
  via an effort map — `none`=512, `low`=1024, `medium`=4096, `high`=12288, `xhigh`=24576, `max`=off.
  Default effort is **low**.
- **No tools / no vision**: both rejected with `400` (`tools_unsupported` / `vision_unsupported`).
- **Context**: 32K native, served at 32,768; max completion 16,000.
- Native output is Thought inside `<think>` … `</think>`, then Solution (`deepseek_r1` parser).

## Thinking, through the gateway
Managed-thinking **budget** mode. Effort is **not** `max_tokens`:
- Client `reasoning_effort` → card `effort_map` → vLLM `thinking_token_budget` (CoT cap).
- `max_tokens` is the OpenAI total-generation ceiling (Thought + Solution). The gateway
  only **raises** it when it is smaller than budget + 512 so the answer can still fit.
- **ON** (default `low`) → CoT in **`reasoning`** (OpenAI) / a **`thinking`** block (Anthropic).
- **OFF** (`reasoning_effort: none`) → budget **512** (not 0 — vLLM#18141) + strip reasoning.
- Phi always emits Thought then Solution; OFF is reduce+strip, not a true skip.

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
- Always-up: `minReplicas: 1`, `maxReplicas: 2`, `scaleTarget: 8`. `--max-num-seqs=8`, util 0.92,
  `VLLM_ATTENTION_BACKEND=TRITON_ATTN_VLLM_V1`.

## Testing
The 31-check budget battery (model is always-up, no wake wait beyond Ready):
```bash
# External via public edge + Tyk auth
GW_URL=https://inference.vulcan.alliancecan.ca GW_INSECURE=1 TYK_KEY=<key> \
  python3 models/phi-4-reasoning/test.py

# Or inside the gateway pod (no auth)
cat models/phi-4-reasoning/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```
Last run (2026-06-18): **26 PASS / 5 EXP / 0 FAIL** — managed thinking ON (budget) / OFF (strip+cap),
streaming reasoning, stop/system, tools-rejected + vision-rejected guards, Anthropic parity,
catalog. (5 EXP = tools-rejected, vision-rejected, embed-via-Anthropic, ANT-tools-rejected, bad-model.)

## Source
[HuggingFace: microsoft/Phi-4-reasoning](https://huggingface.co/microsoft/Phi-4-reasoning) · MIT
