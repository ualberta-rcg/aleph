# ProtGPT2

ProtGPT2 (~1.5B, GPT-2 architecture) generates **novel protein sequences** (amino-acid
strings) from scratch or by continuing a partial prompt. Trained on natural protein sequences.
[HuggingFace](https://huggingface.co/nferruz/ProtGPT2)

## Resource Requirements

| Resource | Request | Limit |
|----------|---------|-------|
| GPU | 1x HAMi slice (L40S) | - |
| Storage | PVC: `protgpt2-data` | - |

## API Endpoint (custom — NOT OpenAI chat)

```bash
curl -X POST http://<gateway>/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"protgpt2","prompt":"","max_tokens":120,"num_sequences":1,"temperature":0.7}'
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

- Non-chat: protein-sequence generation only. No tools / vision / anthropic.
- Requires a non-empty seed prompt (e.g. `"prompt":"M"`, a start methionine); an empty
  prompt crashes the server with a 500 (`reshape tensor of 0 elements`).
- MIT license. GPU float16.
- Validated 2026-06-18 via custom generation battery (`test.py`).
