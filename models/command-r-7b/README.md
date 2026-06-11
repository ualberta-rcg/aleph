# Command R 7B

Cohere Command R 7B RAG-optimized chat model, served via vLLM.
[HuggingFace](https://huggingface.co/CohereForAI/c4ai-command-r7b-12-2024)

## Resource Requirements

| Resource | Request | Limit |
|----------|---------|-------|
| GPU | 1x HAMi slice (L40S) | - |
| Memory | (vLLM managed) | - |
| Storage | PVC: `command-r-7b-data` | - |

## API Endpoint

```bash
curl -X POST http://<gateway>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "command-r-7b",
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

- Multilingual, RAG-optimized
- Custom params: top_p, top_k, repetition_penalty
- 16/16 gateway tests passed (2026-06-10)
