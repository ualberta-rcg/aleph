# Phi-4 Reasoning — Model Context

## What This Model Does

Microsoft Phi-4-reasoning 14B — chain-of-thought reasoning model (math, science, code).
Native format: **Thought** block then **Solution** block. 32K context. Whole single L40S.

Phi **always thinks by training**. There is no Qwen-style `enable_thinking=false`.

**Status:** `production` / always-up (`scale_to_zero: false`, `minReplicas: 1`).

## Runtime

- **Image:** `vllm/vllm-openai:v0.20.2`
- **Args:** `--reasoning-parser=deepseek_r1` (no `--enable-reasoning` — removed in v0.20.2),
  `--reasoning-config` with `<think>` / `</think>`, `--max-num-seqs=8`, util `0.92`
- **Env:** `VLLM_ATTENTION_BACKEND=TRITON_ATTN_VLLM_V1` (L40S / SM89)
- **GPU:** whole L40S (`nvidia.com/gpu: 1`, no `gpumem`)
- **Replicas:** min 1 / max 2 / `scaleTarget: 8` (match `--max-num-seqs`)
- **Timeout:** 600s
- **Weights:** PVC `phi-4-reasoning` (HF init container, gemma-4 venv-on-PVC)

## Gateway integration (do not change gateway.py for this model)

Two different fields — do not conflate them:

| Client field | What it is | What the gateway does | What vLLM does |
|---|---|---|---|
| `reasoning_effort` | Our alias (low/medium/high/…) | Maps via `effort_map` → `thinking_token_budget`, then **pops** `reasoning_effort` | Never sees `reasoning_effort` on this model |
| `thinking_token_budget` | CoT / Thought cap | **Forwards** to vLLM | Caps reasoning tokens; at the cap it forces `</think>` |
| `max_tokens` | OpenAI **total** generation (Thought + Solution) | Default 2048 if unset. If it is **smaller** than `budget + answer_reserve` (512), **raise** it so the answer can fit. Does **not** cap a large client `max_tokens`. Hard ceiling is only `limits.max_completion_tokens` (16000). | Stops the whole completion (reasoning + answer) |

vLLM v0.20.2 docs: `thinking_token_budget` is independent of `max_tokens`. If the budget is omitted, only `max_tokens` limits everything.

Default chat: effort **low** (budget 1024), `max_tokens` 2048, temp 0.8 / top_p 0.95 / top_k 50.

OFF (`reasoning_effort=none`): budget **512** (never 0 — vllm#18141) + strip `reasoning` + existing `off_max_tokens` on the OFF path.

`behavior.strips_thinking: false` — managed-thinking still exposes `reasoning` when ON and strips when OFF.

## Why `content` can be empty (not a gateway bug)

1. **Token budget** — `max_tokens` covers both Thought and Solution. A tiny ceiling can be
   consumed entirely by chain-of-thought before Solution is emitted.
2. **Parser split** — vLLM `deepseek_r1` splits on `<think>` … `</think>` into `reasoning` vs
   `content`. If the model never emits closing tags, both fields are wrong.
3. **Budget 0** — do not send `thinking_token_budget: 0` (vllm#18141 burns tokens / empty content).

**Do not** paper over empty `content` by copying `reasoning` into `content` in the gateway.

## Deploy / test

Never `kubectl patch` the ISVC. Delete, keep PVC, re-apply:

```bash
kubectl delete isvc phi-4-reasoning -n models
# do not delete the PVC
kubectl apply -f models/phi-4-reasoning/inferenceservice.yaml
kubectl apply -f models/phi-4-reasoning/details.yaml

GW_URL=https://inference.vulcan.alliancecan.ca GW_INSECURE=1 TYK_KEY=$TYK_KEY \
  python3 models/phi-4-reasoning/test.py
```

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | Gateway card (schema v2) |
| `inferenceservice.yaml` | KServe/vLLM spec |
| `pvc.yaml` | Model weights PVC |

**Keep `details.yaml` in sync with `inferenceservice.yaml` changes.**
