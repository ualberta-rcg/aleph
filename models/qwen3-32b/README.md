# Qwen3-32B

Qwen3-32B dense model (32.8B params) with thinking mode and tool calling.

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

The 34-check comprehensive battery runs inside the gateway pod (the first check wakes the
model if it's scaled to zero):

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/qwen3-32b/test.py

# Or inside the gateway pod (no auth)
cat models/qwen3-32b/test.py | \
  kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-18): **31 passed, 3 expected, 0 failed** — answer/finish_reason/tool-name/
model-echo/truncation assertions + thinking on/off/budget/stream + meta-tasks + Anthropic
parity + guardrails. (3 EXP = vision-rejected, embed-via-Anthropic, bad-model.)

## Key Configuration

| Setting | Value |
|---------|-------|
| vLLM | v0.20.2 |
| Tensor Parallel | 2 (whole GPU) |
| Context Window | 40,960 tokens |
| Max Completion | 32,768 tokens |
| Reasoning Parser | qwen3 |
| Tool Call Parser | hermes |
| Scale-to-Zero | 15m idle |
| Cold Start | ~3-4 min |

## Thinking Mode (managed by the gateway)

Binary `enable_thinking` switch (a real off, unlike gpt-oss). Gateway maps `reasoning_effort`:
none/low → off, medium/high/max → on. Through the gateway:
- **ON** → chain-of-thought in the **`reasoning`** field (OpenAI) / a **`thinking`** block (Anthropic).
- **OFF** (`reasoning_effort: none`) → no reasoning + `max_tokens` capped to `off_max_tokens` (2048).
