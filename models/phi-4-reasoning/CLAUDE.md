# Phi-4 Reasoning — Model Context

## What This Model Does

Microsoft Phi-4-reasoning 14B — chain-of-thought reasoning model (math, science, code).
Native format: **Thought** block then **Solution** block. 32K context. Whole single L40S.

**Status on cluster 230:** `production` / **PASS** (OpenAI + Anthropic via gateway).

## Runtime

- **Image:** `vllm/vllm-openai:v0.20.2`
- **Args:** `--reasoning-parser=deepseek_r1` (no `--enable-reasoning` — removed in v0.20.2)
- **GPU:** whole L40S (`nvidia.com/gpu: 1`, no `gpumem`)
- **Cold start:** ~3–5 min; `progress-deadline: 2400s`
- **Weights:** PVC `phi-4-reasoning-data` (HF init container)

## Gateway integration

- Card `schema_version: 2`; `param_translation.thinking.mode: always_on`
- `behavior.strips_thinking: true` — strips `reasoning`/`reasoning_content` after vLLM split
- Use `max_tokens` ≥ 4096 for real reasoning tasks (Thought + Solution share one budget)
- Gateway does **not** remap reasoning→content; empty `content` means fix vLLM/parser/budget

## Why `content` can be empty (not a gateway bug)

Three separate causes, often confused:

1. **Token budget** — `max_tokens` covers both Thought and Solution. A 200–600 token
   budget can be consumed entirely by chain-of-thought before Solution is emitted.
2. **Parser split** — Microsoft expects `` … `` then Solution. vLLM
   `deepseek_r1` parser splits on those tokens into `reasoning` vs `content`. If the
   model never emits closing tags (known vLLM V1 issue, vllm#18141), both fields are wrong.
3. **No separate reasoning budget on v0.20.2** — unlike Qwen3/DeepSeek in newer vLLM,
   Phi-4 does not get `thinking_token_budget`; only total `max_tokens` applies.

**Do not** paper over empty `content` by copying `reasoning` into `content` in the gateway.
Fix: raise `max_tokens`, ensure parser/tags work, or add Phi-specific vLLM config.

## Deploy / test

```bash
kubectl apply -f models/phi-4-reasoning/pvc.yaml
kubectl apply -f models/phi-4-reasoning/details.yaml
kubectl apply -f models/phi-4-reasoning/inferenceservice.yaml

curl -X POST http://<gateway>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"phi-4-reasoning","messages":[{"role":"user","content":"What is 12*8?"}],"max_tokens":4096}'
```

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | Gateway card (schema v2) |
| `inferenceservice.yaml` | KServe/vLLM spec |
| `pvc.yaml` | Model weights PVC |

**Keep `details.yaml` in sync with `inferenceservice.yaml` changes.**
