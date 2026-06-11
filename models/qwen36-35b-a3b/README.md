# Qwen3.6-35B-A3B

Qwen3.6-35B-A3B — hybrid Gated-DeltaNet MoE (3B active) with thinking, tools & vision (2× L40S).

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
cat test.py | kubectl exec -i -n models <gateway-pod> -c gateway -- tee /tmp/test_qwen36_35b_a3b.py

# Run (pod must be warm — wake with a request first if scaled to zero)
kubectl exec -n models <gateway-pod> -c gateway -- python3 /tmp/test_qwen36_35b_a3b.py
```

Expected: **21 passed, 2 expected failures, 0 failed**

## Key Configuration

| Setting | Value |
|---------|-------|
| vLLM | v0.20.2 |
| Tensor Parallel | 2 (whole GPU) |
| Context Window | 32,768 tokens |
| Max Completion | 32,768 tokens |
| Reasoning Parser | qwen3 (effort mode, not on by default) |
| Tool Call Parser | qwen3_coder |
| Vision | Yes (images + video via ViT encoder) |
| Scale-to-Zero | 15m idle |
| Cold Start | ~5 minutes |

## Model Highlights

- **Hybrid architecture**: 30 Gated DeltaNet (linear attention) + 10 full softmax attention layers
- **MoE efficiency**: 35B total params, only 3B active per token (256 experts, 8+1 routed)
- **Full multimodal**: Thinking + tools (qwen3_coder) + vision (images + video)
- **256K native context**: Deployed at 32K, extendable with YaRN to 1M
- **Thinking controlled via API**: `chat_template_kwargs: {enable_thinking: true/false}`
- **Apache-2.0** license
