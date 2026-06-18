# Qwen2.5-VL-72B-Instruct (AWQ)

Qwen2.5-VL-72B-Instruct, **AWQ-quantized** large vision-language model (text + image). vLLM backend.
[HuggingFace](https://huggingface.co/Qwen/Qwen2.5-VL-72B-Instruct-AWQ)

## Resource Requirements

| Resource | Request | Limit |
|----------|---------|-------|
| GPU | 2x L40S (TP2, AWQ 4-bit ~40 GB) | - |
| Storage | PVC: `qwen25-vl-72b-awq-data` | - |

## API Endpoint

```bash
curl -X POST http://<gateway>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen25-vl-72b-awq",
    "messages": [{"role": "user", "content": [{"type":"text","text":"What is in this image?"},{"type":"image_url","image_url":{"url":"data:image/png;base64,..."}}]}],
    "max_tokens": 100
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

- Multimodal: vision supported. Tools: not supported. Reasoning: no.
- AWQ 4-bit quantization (smaller footprint than BF16 qwen25-vl-72b).
- Validated 2026-06-18 via comprehensive gateway battery (`test.py`).
