# Qwen2.5-Coder-32B

Qwen2.5-Coder-32B-Instruct — code generation, reasoning & repair specialist with tool calling (2× L40S).

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
cat test.py | kubectl exec -i -n models <gateway-pod> -c gateway -- tee /tmp/test_qwen25_coder_32b.py

# Run (pod must be warm — wake with a request first if scaled to zero)
kubectl exec -n models <gateway-pod> -c gateway -- python3 /tmp/test_qwen25_coder_32b.py
```

Expected: **22 passed, 3 expected failures, 0 failed**

## Key Configuration

| Setting | Value |
|---------|-------|
| vLLM | v0.20.2 |
| Tensor Parallel | 2 (whole GPU) |
| Context Window | 32,768 tokens |
| Max Completion | 32,768 tokens |
| Reasoning Parser | None (non-reasoning model) |
| Tool Call Parser | hermes |
| Scale-to-Zero | 15m idle |
| Cold Start | ~3 minutes |

## Model Highlights

- **Code specialist**: Trained on 5.5T tokens of source code, text-code grounding, and synthetic data
- **State-of-the-art**: Matches GPT-4o on coding benchmarks
- **Tool calling**: Supports function calling via hermes parser for code agent workflows
- **131K context**: Native 131K tokens (deployed at 32K), YaRN available for longer contexts
- **No reasoning mode**: Direct code generation without thinking/reasoning blocks
