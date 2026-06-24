# AstroSage-8B

AstroSage-8B — Llama-3.1-8B fine-tuned on astronomy/astrophysics. Beats GPT-4o on astro benchmarks (80.9%).
[HuggingFace](https://huggingface.co/AstroMLab/AstroSage-8B)

## Resource Requirements

| Resource | Value |
|----------|-------|
| GPU | 1x L40S vGPU slice (16GB) |
| Storage | PVC: `astrosage-data` (NFS, ReadWriteMany) |
| Server | Custom FastAPI (transformers, NOT vLLM) |
| TP | N/A (single GPU slice) |

## API Endpoint

```bash
curl -X POST http://<gateway>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "astrosage",
    "messages": [{"role": "user", "content": "What is a black hole?"}],
    "max_tokens": 200
  }'
```

## Scaling & Context

| Setting | Value |
|---------|-------|
| minReplicas | 0 (scale to zero) |
| idle_retention | 15m |
| Context Window | 8K (8192 tokens) |
| max_completion_tokens | 8000 |
| Streaming | No (no_stream=true) |
| Tools | No |
| Cold start | ~2-3 min (venv cached) |

## Deploy

```bash
kubectl apply -f pvc.yaml
kubectl apply -f details.yaml
kubectl apply -f inferenceservice.yaml
```

## Notes

- 8B dense, Llama-3.1-8B fine-tuned on 250K+ arXiv astronomy papers (3.3B tokens) + 8.8M QA pairs (2B tokens)
- Custom FastAPI server using transformers `pipeline("text-generation")` — NOT vLLM
- HAMi vGPU slice: 16GB of 48GB L40S (shares GPU with other workloads)
- No streaming support — gateway forces non-streaming responses
- NFS PVC (ReadWriteMany) for venv + model weights
- 14/14 gateway tests passed (2026-06-10)

## Testing
The non-reasoning battery runs inside the gateway pod (first check wakes a scaled-to-zero model):
```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> MODEL=astrosage python3 models/astrosage/test.py

# Or inside the gateway pod (no auth)
cat models/astrosage/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```
Last run (2026-06-18): **18 PASS / 4 EXP / 0 FAIL (custom backend — model-echo only)**

