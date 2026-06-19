# OpenBioLLM-70B

Llama 3 70B fine-tuned for biomedical and clinical NLP.
[HuggingFace](https://huggingface.co/aaditya/Llama3-OpenBioLLM-70B)

## Resource Requirements

| Resource | Value |
|----------|-------|
| GPU | 4x L40S (TP=4, whole device) |
| Storage | PVC: `openbiollm-70b-data` |
| vLLM | v0.20.2 |
| TP | 4 |
| Cold start | ~7 minutes |

## API Endpoint

```bash
curl -X POST http://<gateway>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openbiollm-70b",
    "messages": [{"role": "user", "content": "What is hypertension?"}],
    "max_tokens": 120
  }'
```

## Scaling & Context

| Setting | Value |
|---------|-------|
| minReplicas | 0 (scale to zero) |
| idle_retention | 15m |
| Context Window | 8192 (native max, no rope scaling) |
| max_completion_tokens | 8000 |
| Streaming | Yes |

## Deploy

```bash
kubectl apply -f details.yaml
kubectl apply -f inferenceservice.yaml
```

## Notes

- Uses ALL 4 L40S GPUs (TP=4) — no other GPU models can run simultaneously
- Llama 3 70B base, no rope scaling — 8K is the hard context limit
- 14/14 gateway tests passed (2026-06-10)

## Testing
The non-reasoning battery runs inside the gateway pod (first check wakes a scaled-to-zero model):
```bash
cat models/openbiollm-70b/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```
Last run (2026-06-18): **19 PASS / 4 EXP / 0 FAIL (70B TP4 — slow cold-start, patient wake)**

