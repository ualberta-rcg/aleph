# Qwen2.5-VL-3B

Qwen2.5-VL-3B-Instruct — compact vision-language model for images, video, OCR & docs (1× GPU slice).

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
cat test.py | kubectl exec -i -n models <gateway-pod> -c gateway -- tee /tmp/test_qwen25_vl_3b.py

# Run (pod must be warm — wake with a request first if scaled to zero)
kubectl exec -n models <gateway-pod> -c gateway -- python3 /tmp/test_qwen25_vl_3b.py
```

Expected: **18 passed, 2 expected failures, 0 failed**

## Key Configuration

| Setting | Value |
|---------|-------|
| vLLM | v0.20.2 |
| Tensor Parallel | 1 (HAMi vGPU slice) |
| GPU Memory | 24 GB (gpumem) |
| Context Window | 4,096 tokens |
| Max Completion | 2,048 tokens |
| Reasoning Parser | None (non-reasoning model) |
| Tool Call Parser | None (no tool calling) |
| Vision | Yes (images, up to 4 per prompt) |
| Scale-to-Zero | 15m idle |
| Cold Start | ~2 minutes |

## Model Highlights

- **Vision-language**: Dynamic resolution images, video, OCR, chart/document parsing
- **Ultra-compact**: 3B dense + ViT, fits on a single HAMi GPU slice (24 GB)
- **No tool calling**: Visual grounding only, not structured function calling
- **4K context**: Conservative for VRAM efficiency with vision inputs
- **Apache-2.0** license
