# SPECTER2 (allenai/specter2_base)

AllenAI **SPECTER2** — scientific paper embedding model (SciBERT backbone further trained on
~6M citation triplets across 23 fields). Takes title+abstract, produces **768-dim mean-pooled
embeddings** for paper search, citation recommendation, and document clustering. Custom
FastAPI/transformers server, CPU-only, always-on (minReplicas: 1).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX weights + venv (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/specter2/test.py

# Or inside the gateway pod (no auth)
cat models/specter2/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 768, batch, model-echo, usage,
distinctness, encoding_format, truncation, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` (CPU) |
| Endpoint | `POST /v1/embeddings`, health `/health` |
| Embedding dim | 768 (mean-pooled) |
| Max input | 512 tokens |
| Parameters | 110M (SciBERT backbone) |
| Scale | always-on (`minReplicas: 1`, max 3, 15m retention) |
| Weights | PVC `specter2` (RWX, nfs-models; bare fleet naming) |
