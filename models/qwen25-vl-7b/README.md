# Qwen2.5-VL-7B

Qwen2.5-VL-7B-Instruct — compact vision-language model with tool calling, images + video (1× GPU slice).

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
cat test.py | kubectl exec -i -n models <gateway-pod> -c gateway -- tee /tmp/test_qwen25_vl_7b.py

# Run (pod must be warm — wake with a request first if scaled to zero)
kubectl exec -n models <gateway-pod> -c gateway -- python3 /tmp/test_qwen25_vl_7b.py
```

Expected: **22 passed, 2 expected failures, 0 failed**

## Key Configuration

| Setting | Value |
|---------|-------|
| vLLM | v0.20.2 |
| Tensor Parallel | 1 (HAMi vGPU slice) |
| GPU Memory | 32 GB (gpumem) |
| Context Window | 65,536 tokens |
| Max Completion | 16,384 tokens |
| Reasoning Parser | None (non-reasoning model) |
| Tool Call Parser | hermes |
| Vision | Yes (images + video, up to 20 images, 1 video) |
| Scale-to-Zero | 15m idle |
| Cold Start | ~2 minutes |

## Model Highlights

- **Vision-language**: Dynamic resolution images, video up to 1+ hour, OCR, chart parsing
- **Compact**: 7B dense + ViT, fits on a single HAMi GPU slice (32 GB)
- **Tool calling**: Hermes parser for function calling (conservative on tool_choice='auto')
- **65K context**: Extended beyond native 32K using MRoPE position encoding
- **Apache-2.0** license
