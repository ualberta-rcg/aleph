# ScINCL (malteos/scincl)

Scientific-text embedding model trained with **in-category learning on citation triplets** — strong
for scientific document similarity, citation recommendation, and classification. 768-dim
[CLS]-pooled embeddings. Custom FastAPI/transformers server on a HAMi GPU slice, scale-to-zero.
OpenAI-compliant `/v1/embeddings` (batch + usage).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + HF cache (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/scincl/test.py

# Or inside the gateway pod (no auth)
cat models/scincl/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 768, batch, model-echo, usage,
distinctness, encoding_format, truncation, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` AutoModel (GPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped; `input`/`texts`), health `/health` |
| Embedding dim | 768 ([CLS]-pooled) |
| Max input | 512 tokens |
| Parameters | 110M |
| GPU | HAMi slice 10 GiB (`nvidia.com/gpumem: 10240`) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `scincl-data` (RWX, nfs-models; migrated from RWO) |
