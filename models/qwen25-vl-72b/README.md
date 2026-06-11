# Qwen2.5-VL-72B

Qwen2.5-VL-72B-Instruct — large vision-language model for images, video & visual grounding (4× L40S).

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
cat test.py | kubectl exec -i -n models <gateway-pod> -c gateway -- tee /tmp/test_qwen25_vl_72b.py

# Run (pod must be warm — wake with a request first if scaled to zero)
kubectl exec -n models <gateway-pod> -c gateway -- python3 /tmp/test_qwen25_vl_72b.py
```

Expected: **22 passed, 2 expected failures, 0 failed**

## Key Configuration

| Setting | Value |
|---------|-------|
| vLLM | v0.20.2 |
| Tensor Parallel | 4 (whole GPU) |
| Context Window | 32,768 tokens |
| Max Completion | 32,768 tokens |
| Reasoning Parser | None (non-reasoning model) |
| Tool Call Parser | None (no tool calling) |
| Vision | Yes (images + video, up to 5 per prompt) |
| Scale-to-Zero | 15m idle |
| Cold Start | ~4 minutes |

## Model Highlights

- **Vision-language**: Dynamic resolution images, video up to 1+ hour, multiple images per prompt
- **72.2B dense**: State-of-the-art VLM, GQA (64Q/8KV), 80 layers
- **Visual grounding**: Bounding box support for GUI agent use cases
- **No tool calling**: Visual grounding only, not structured function calling
- **131K context**: Native 32K, YaRN to 131K (not recommended for VL tasks)
