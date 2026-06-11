# TinyLlama-1.1B

TinyLlama-1.1B-Chat served via llama-cpp-python (CPU inference).
[HuggingFace](https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF)

## Resource Requirements

| Resource | Request | Limit |
|----------|---------|-------|
| CPU | 4 | 8 |
| Memory | 3Gi | 4Gi |
| GPU | None (CPU only) | - |
| Storage | 5Gi (PVC: `tinyllama-1-1b-models`) | - |

## API Endpoint

```bash
# Chat completion (via gateway)
curl -X POST http://<gateway>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tinyllama-1-1b",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }'

# Anthropic-style (gateway translates)
curl -X POST http://<gateway>/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tinyllama-1-1b",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }'
```

## Scaling Configuration

| Setting | Value |
|---------|-------|
| minReplicas | 0 (scale to zero) |
| idle_retention | 15m |
| Context Window | 4096 tokens |
| Streaming | No (gateway forces stream=false) |

## Deploy

```bash
kubectl apply -f details.yaml
kubectl apply -f inferenceservice.yaml
kubectl get inferenceservice tinyllama-1-1b -n models
```

## Notes

- GGUF format (Q4_K_M quantization, ~638MB)
- Streaming disabled (`no_stream: true` in card)
- CPU-only workload — no GPU scheduling
- Init container downloads GGUF on first boot
- 14/14 gateway tests passed (2026-06-10)
