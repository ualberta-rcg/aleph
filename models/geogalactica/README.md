# GeoGalactica 30B

GeoGalactica 30B — geoscience LLM, further pre-trained Galactica on 65B geo tokens.
[HuggingFace](https://huggingface.co/geobrain-ai/geogalactica)

## Resource Requirements

| Resource | Value |
|----------|-------|
| GPU | 2x L40S (TP=2, whole-device) |
| Storage | PVC: `geogalactica` |
| vLLM | v0.20.2 |
| TP | 2 |

## API Endpoint

```bash
curl -X POST http://<gateway>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "geogalactica",
    "messages": [{"role": "user", "content": "What is the Mohs hardness scale?"}],
    "max_tokens": 100
  }'
```

## Scaling & Context

| Setting | Value |
|---------|-------|
| minReplicas | 0 (scale to zero) |
| idle_retention | 15m |
| Context Window | 2K (2048 tokens, hard limit) |
| max_completion_tokens | 2000 |
| Streaming | Yes (SSE) |
| Tools | No |
| Cold start | ~7 minutes (30B, 13 shards) |

## Deploy

```bash
kubectl apply -f details.yaml
kubectl apply -f inferenceservice.yaml
```

## Notes

- 30B dense, OPT/Galactica architecture — 48 layers, 56 heads
- Geoscience domain: geology, mineralogy, earth science Q&A
- Very short context (2048) — OPT positional embedding limit, cannot extend
- Custom `chat_template.jinja` mounted from PVC
- `--disable-custom-all-reduce` required for L40S PCIe topology
- 14/14 gateway tests passed (2026-06-10)

## Testing
The non-reasoning battery runs inside the gateway pod (first check wakes a scaled-to-zero model):
```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/geogalactica/test.py

# Or inside the gateway pod (no auth)
cat models/geogalactica/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```
Last run (2026-06-18): **19 PASS / 4 EXP / 0 FAIL (base OPT — slow cold-start, patient wake)**

