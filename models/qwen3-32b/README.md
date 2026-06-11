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

The test runs from the gateway pod against the in-cluster gateway endpoint.

```bash
# Copy test to gateway pod
cat test.py | kubectl exec -i -n models <gateway-pod> -c gateway -- tee /tmp/test_qwen3_32b.py

# Run (pod must be warm — wake with a request first if scaled to zero)
kubectl exec -n models <gateway-pod> -c gateway -- python3 /tmp/test_qwen3_32b.py
```

Expected: **23 passed, 2 expected failures, 0 failed**

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

## Thinking Mode

Controlled via `chat_template_kwargs.enable_thinking` (binary on/off):
- Default: **on** (thinking enabled)
- Off: `{"chat_template_kwargs": {"enable_thinking": false}}`
- Gateway maps `reasoning_effort` parameter: none/low → off, medium/high/max → on
