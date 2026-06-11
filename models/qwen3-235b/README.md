# Qwen3-235B

Qwen3 235B A22B MoE (235B total / 22B active, AWQ int4) — non-thinking instruct variant with tool calling.

## Deployment

```bash
# Apply PVC (if not already created)
kubectl apply -f pvc.yaml

# Apply InferenceService
kubectl apply -f inferenceservice.yaml

# Apply model card ConfigMap
kubectl apply -f details.yaml
```

**Note**: This model requires all 4 GPUs on a node (TP4). It cannot run simultaneously with other TP4 models.

## Testing

The test runs from the gateway pod against the in-cluster gateway endpoint.

```bash
# Copy test to gateway pod
cat test.py | kubectl exec -i -n models <gateway-pod> -c gateway -- tee /tmp/test_qwen3_235b.py

# Run (pod must be warm — wake with a request first if scaled to zero)
kubectl exec -n models <gateway-pod> -c gateway -- python3 /tmp/test_qwen3_235b.py
```

Expected: **21 passed, 3 expected failures, 0 failed**

## Key Configuration

| Setting | Value |
|---------|-------|
| vLLM | v0.20.2 |
| Tensor Parallel | 4 (whole GPU) |
| Quantization | awq_marlin (AWQ int4) |
| Context Window | 131,072 tokens |
| Max Completion | 32,768 tokens |
| Tool Call Parser | hermes |
| Reasoning Parser | none (non-thinking variant) |
| Scale-to-Zero | 30m idle |
| Cold Start | ~4 minutes |

## Thinking Mode

This is the **non-thinking instruct variant** (Instruct-2507). It does NOT support reasoning/thinking mode and will not generate `<think` blocks. No `--reasoning-parser` flag is needed.

## Recommended Sampling

Per HuggingFace docs: `temperature=0.7`, `top_p=0.8`, `top_k=20`.
