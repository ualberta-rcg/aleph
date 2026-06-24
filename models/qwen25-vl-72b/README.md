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

The 24-check vision battery runs inside the gateway pod (first check wakes a scaled-to-zero model —
144 GB BF16 loads slowly, give it a patient wake):

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/qwen25-vl-72b/test.py

# Or inside the gateway pod (no auth)
cat models/qwen25-vl-72b/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-18): **21 PASS / 2 EXP / 0 FAIL** — image vision, streaming, temp/stop/system,
meta-tasks, Anthropic parity, guardrails. (2 EXP = vision-guard + embed-guard; +1 SKIP embed-cold.)

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
