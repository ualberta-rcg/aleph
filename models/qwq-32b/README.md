# QwQ-32B

Qwen QwQ-32B — dedicated reasoning model with always-on chain-of-thought and tool calling (2× L40S).

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

The 22-check always-on battery runs inside the gateway pod (first check wakes a scaled-to-zero model):

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/qwq-32b/test.py

# Or inside the gateway pod (no auth)
cat models/qwq-32b/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-18): **19 PASS / 3 EXP / 0 FAIL** — always-on reasoning exposed by default,
stripped + off-capped on `reasoning_effort: none` / meta-tasks, tools, streaming reasoning,
answer/tool-name/model-echo/truncation assertions, Anthropic parity, guardrails. (Meta title/tags
may return empty content — qwq thinks so heavily that stripped output is short; the test asserts
reasoning is stripped, not content non-empty.)

## Key Configuration

| Setting | Value |
|---------|-------|
| vLLM | v0.20.2 |
| Tensor Parallel | 2 (whole GPU) |
| Context Window | 32,768 tokens |
| Max Completion | 32,768 tokens |
| Reasoning Parser | deepseek_r1 (always-on thinking) |
| Tool Call Parser | hermes |
| Scale-to-Zero | 15m idle |
| Cold Start | ~2 minutes |

## Thinking Mode

QwQ-32B **always reasons** — it always generates `<think/>` chain-of-thought blocks. There is no toggle to disable this. The deepseek_r1 reasoning parser handles the thinking content in API responses. No `enable_thinking` parameter or reasoning_effort control.

## Recommended Sampling

Per HuggingFace docs: `temperature=0.6`, `top_p=0.95`, `top_k=20-40`. Do NOT use greedy decoding (causes repetitions).
