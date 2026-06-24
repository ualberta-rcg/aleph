# DeepSeek V2 Lite 16B

DeepSeek V2 Lite 16B MoE Chat — compact MoE with Multi-head Latent Attention (MLA).
[HuggingFace](https://huggingface.co/deepseek-ai/DeepSeek-V2-Lite-Chat)

## Resource Requirements

| Resource | Value |
|----------|-------|
| GPU | 1x HAMi slice (L40S, 48GB) |
| Storage | PVC: `deepseek-v2-lite-16b` |
| vLLM | v0.20.2 |
| TP | 1 |

## API Endpoint

```bash
curl -X POST http://<gateway>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v2-lite-16b",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }'
```

## Scaling & Context

| Setting | Value |
|---------|-------|
| minReplicas | 0 (scale to zero) |
| idle_retention | 15m |
| Context Window | 128K (131072 tokens) |
| max_completion_tokens | 8000 |
| Streaming | Yes |

## Deploy

```bash
kubectl apply -f pvc.yaml
kubectl apply -f details.yaml
kubectl apply -f inferenceservice.yaml
```

## Notes

- 15.7B total (2.4B active), MoE with MLA — efficient KV cache
- Bilingual English/Chinese, strong at reasoning and code
- MLA compression: ~30KB/token KV, 481K token KV capacity on single L40S
- 14/14 gateway tests passed (2026-06-10)

## Testing
The non-reasoning battery runs inside the gateway pod (first check wakes a scaled-to-zero model):
```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/deepseek-v2-lite-16b/test.py

# Or inside the gateway pod (no auth)
cat models/deepseek-v2-lite-16b/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```
Last run (2026-06-18): **14 PASS / 0 FAIL (MLA, TP1, no --enforce-eager)**

