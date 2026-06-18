# GLM-4-32B-0414

Zhipu GLM-4-32B-0414 — strong **function calling + agentic workflows**. vLLM backend (TP2).
[HuggingFace](https://huggingface.co/THUDM/GLM-4-32B-0414)

## Resource Requirements

| Resource | Request | Limit |
|----------|---------|-------|
| GPU | 2x L40S (TP2, 32B dense ~64 GB) | - |
| Storage | PVC: `glm-4-32b-data` | - |

## API Endpoint

```bash
curl -X POST http://<gateway>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-4-32b",
    "messages": [{"role": "user", "content": "What is the weather in Edmonton?"}],
    "tools": [{"type":"function","function":{"name":"get_weather","parameters":{"type":"object","properties":{"city":{"type":"string"}}}}}],
    "max_tokens": 200
  }'
```

## Scaling

| Setting | Value |
|---------|-------|
| minReplicas | 0 (scale to zero) |
| idle_retention | 15m |
| Context Window | 32768 tokens |
| Streaming | Yes |

## Deploy

```bash
kubectl apply -f details.yaml
kubectl apply -f inferenceservice.yaml
```

## Notes

- Tools: supported (function calling / agents). Vision: not supported. Reasoning: no.
- Custom params passthrough (top_p, top_k, temperature).
- Validated 2026-06-18 via comprehensive gateway battery (`test.py`).
