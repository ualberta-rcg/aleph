# TinyLlama-1.1B

TinyLlama-1.1B-Chat served via llama-cpp-python (CPU inference).
[HuggingFace](https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF)

## Resource Requirements

| Resource | Request | Limit |
|----------|---------|-------|
| CPU | 2 | 8 |
| Memory | 3Gi | 4Gi |
| GPU | None (CPU only) | - |
| Storage | 5Gi | - |

## API Endpoint

```bash
# List models
curl https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/models

# Chat completion
curl https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tinyllama-1.1b",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }'
```

## Scaling Configuration

| Setting | Value |
|---------|-------|
| minReplicas | 1 |
| Context Window | 4096 tokens |
| Gateway Truncation | 3800 tokens |

## Deploy

```bash
kubectl apply -k .
kubectl get inferenceservice tinyllama -n models
```

## Notes

- GGUF format (Q4_K_M quantization, ~638MB)
- Streaming disabled by gateway (`NO_STREAM_MODELS`)
- Scheduled on `NVIDIA-L40S-SHARED` nodes (CPU-only workload)
- Image pinned by digest to avoid upstream breakage
- Init container downloads GGUF on first boot
