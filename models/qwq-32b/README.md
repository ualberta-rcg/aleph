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

The test runs from the gateway pod against the in-cluster gateway endpoint.

```bash
# Copy test to gateway pod
cat test.py | kubectl exec -i -n models <gateway-pod> -c gateway -- tee /tmp/test_qwq_32b.py

# Run (pod must be warm — wake with a request first if scaled to zero)
kubectl exec -n models <gateway-pod> -c gateway -- python3 /tmp/test_qwq_32b.py
```

Expected: **21 passed, 3 expected failures, 0 failed**

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
