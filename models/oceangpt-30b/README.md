# OceanGPT-30B

OceanGPT 30B MoE — ocean and marine science LLM with tool calling.
[HuggingFace](https://huggingface.co/zjunlp/OceanGPT-basic-30B-A3B-Instruct)

## Resource Requirements

| Resource | Value |
|----------|-------|
| GPU | 2x L40S (TP=2, whole-device) |
| Storage | PVC: `oceangpt-30b-data` |
| vLLM | v0.20.2 |
| TP | 2 |

## API Endpoint

```bash
# Basic chat
curl -X POST http://<gateway>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "oceangpt-30b",
    "messages": [{"role": "user", "content": "What causes ocean acidification?"}],
    "max_tokens": 100
  }'

# With tools
curl -X POST http://<gateway>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "oceangpt-30b",
    "messages": [{"role": "user", "content": "Sea temperature in the Pacific?"}],
    "tools": [{"type": "function", "function": {"name": "get_sea_temperature", "parameters": {"type": "object", "properties": {"location": {"type": "string"}}}}}],
    "max_tokens": 80
  }'
```

## Scaling & Context

| Setting | Value |
|---------|-------|
| minReplicas | 0 (scale to zero) |
| idle_retention | 15m |
| Context Window | 64K (65536 tokens) |
| max_completion_tokens | 64000 |
| Streaming | Yes (SSE) |
| Tools | Yes (hermes parser) |

## Deploy

```bash
kubectl apply -f details.yaml
kubectl apply -f inferenceservice.yaml
```

## Notes

- 30.5B total (3B active), Qwen3 MoE (128 experts, 8 active per token)
- Bilingual English/Chinese, ocean science domain
- `--disable-custom-all-reduce` required for L40S PCIe topology
- `--tool-call-parser=hermes` + `--enable-auto-tool-choice` for function calling
- Works on both OpenAI and Anthropic gateway endpoints
- 14/14 gateway tests passed (2026-06-10)
