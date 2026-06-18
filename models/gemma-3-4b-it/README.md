# Gemma 3 4B IT

Google Gemma 3 4B instruction-tuned **multimodal** model (text + image). vLLM backend.
[HuggingFace](https://huggingface.co/google/gemma-3-4b-it)

## Resource Requirements

| Resource | Request | Limit |
|----------|---------|-------|
| GPU | 1x HAMi slice (L40S) | - |
| Storage | PVC: `gemma-3-4b-it-data` | - |

## API Endpoint

```bash
curl -X POST http://<gateway>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-3-4b-it",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }'
```

## Scaling

| Setting | Value |
|---------|-------|
| minReplicas | 0 (scale to zero) |
| idle_retention | 15m |
| Context Window | 65536 tokens |
| Streaming | Yes |

## Deploy

```bash
kubectl apply -f details.yaml
kubectl apply -f inferenceservice.yaml
```

## Notes

- Multimodal: vision supported (image_url content blocks). Tools: not supported. Reasoning: no.
- Validated 2026-06-18 via comprehensive gateway battery (`test.py`).
