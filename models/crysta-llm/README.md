# CrystaLLM

CrystaLLM-pi_base (~25M, GPT-2 architecture) generates crystal structures in **CIF format**
from a chemical formula prompt. Uses a custom character-level CIF tokenizer (vocab=377).
[HuggingFace](https://huggingface.co/c-bone/CrystaLLM-pi_base)

## Resource Requirements

| Resource | Request | Limit |
|----------|---------|-------|
| GPU | 1x HAMi slice (L40S) | - |
| Storage | PVC: `crysta-llm-data` | - |

## API Endpoint (custom — NOT OpenAI chat)

```bash
curl -X POST http://<gateway>/v1/science/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"crysta-llm","formula":"NaCl","max_new_tokens":400,"num_samples":1,"temperature":1.0}'
```

## Scaling

| Setting | Value |
|---------|-------|
| minReplicas | 0 (scale to zero) |
| idle_retention | 15m |
| Context Window | 1024 tokens |
| Streaming | No |

## Deploy

```bash
kubectl apply -f details.yaml
kubectl apply -f inferenceservice.yaml
```

## Notes

- Non-chat: crystal-structure generation only (CIF output). No tools / vision / anthropic.
- MIT license. ~25M params, GPU float16.
- Validated 2026-06-18 via custom generation battery (`test.py`).
