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
- `behavior.strips_thinking: true` — gateway promotes reasoning→content when parser
  leaves `content` empty, then strips duplicate reasoning fields
- Use `max_tokens` ≥ 4096 for real reasoning tasks; small budgets exhaust on CoT

## Known mapping quirk (not a serving failure)

vLLM's `deepseek_r1` parser targets DeepSeek-R1 token format; Phi-4 uses Thought/Solution
sections instead. Parser often fails to split `reasoning_content` vs `content`. Model still
answers correctly; gateway fill+strip handles the common empty-content case.

**Future TLC:** try a Phi-specific parser when vLLM adds one, or post-process Solution block.

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
