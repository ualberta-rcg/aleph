# Qwen3.5-122B

Qwen3.5 122B MoE FP8 (122B total / 10B active) with toggle thinking mode and native tool calling.

## Deployment

```bash
# Apply PVC (if not already created)
kubectl apply -f pvc.yaml

# Apply InferenceService
kubectl apply -f inferenceservice.yaml

# Apply model card ConfigMap
kubectl apply -f details.yaml
```

## Testing

The 29-check battery runs inside the gateway pod (the first check wakes a scaled-to-zero model):

```bash
cat models/qwen35-122b/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-18): **26 PASS / 3 EXP / 0 FAIL** — tools, managed thinking ON/OFF/budget/stream,
answer/finish_reason/model-echo/truncation assertions, Anthropic parity, guardrails.

## Key Configuration

| Setting | Value |
|---------|-------|
| vLLM | v0.20.2 |
| Tensor Parallel | 4 (whole GPU) |
| Context Window | 131,072 tokens |
| Max Completion | 32,768 tokens |
| Reasoning Parser | qwen3 |
| Tool Call Parser | qwen3_coder |
| Scale-to-Zero | 30m idle |
| Cold Start | ~5 min |

## Thinking Mode

Controlled via `chat_template_kwargs.enable_thinking` (binary toggle):
- Default: **on** (thinking enabled)
- Off: `{"chat_template_kwargs": {"enable_thinking": false}}`
- Gateway toggle mode: maps `thinking.enabled` → `enable_thinking` boolean
