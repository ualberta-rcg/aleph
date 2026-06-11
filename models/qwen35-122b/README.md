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

The test runs from the gateway pod against the in-cluster gateway endpoint.

```bash
# Copy test to gateway pod
cat test.py | kubectl exec -i -n models <gateway-pod> -c gateway -- tee /tmp/test_qwen35_122b.py

# Run (pod must be warm — wake with a request first if scaled to zero)
kubectl exec -n models <gateway-pod> -c gateway -- python3 /tmp/test_qwen35_122b.py
```

Expected: **23 passed, 3 expected failures, 0 failed**

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
