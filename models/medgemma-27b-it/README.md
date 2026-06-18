# MedGemma 27B IT

Google MedGemma 27B instruction-tuned **multimodal** model for medical / radiology use
(text + medical images). vLLM backend (TP2).
[HuggingFace](https://huggingface.co/google/medgemma-27b-it)

## Resource Requirements

| Resource | Request | Limit |
|----------|---------|-------|
| GPU | 2x L40S (TP2, 27B ~54 GB) | - |
| Storage | PVC: `medgemma-27b-it-data` | - |

## API Endpoint

```bash
curl -X POST http://<gateway>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "medgemma-27b-it",
    "messages": [{"role": "user", "content": [{"type":"text","text":"Describe this image."},{"type":"image_url","image_url":{"url":"data:image/png;base64,..."}}]}],
    "max_tokens": 100
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

- Multimodal: vision supported (medical imaging). Tools: not supported. Reasoning: no.
- Research use — not for unsupervised clinical decisions.
- Validated 2026-06-18 via comprehensive gateway battery (`test.py`).
