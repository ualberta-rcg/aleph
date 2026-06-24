# SapBERT (cambridgeltl/SapBERT-from-PubMedBERT-fulltext)

Self-alignment pre-trained on PubMedBERT for **biomedical entity linking** — maps biomedical
mentions (diseases, drugs, etc.) to UMLS concept embeddings. **768-dim [CLS] entity embeddings**
(max 25 tokens). Custom FastAPI/transformers server on a HAMi GPU slice, scale-to-zero. Serves the
standard OpenAI `/v1/embeddings` (`/v1/science/embed` kept as secondary).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + model (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/sapbert/test.py

# Or inside the gateway pod (no auth)
cat models/sapbert/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **6 PASS / 2 EXP / 0 FAIL** — dim 768, batch, model-echo, usage,
distinctness, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` AutoModel (GPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI; + `/v1/science/embed` secondary) |
| Embedding dim | 768 ([CLS]-pooled) |
| Max input | 25 tokens (entity mentions — short) |
| Parameters | 110M |
| GPU | HAMi slice 8 GiB (`nvidia.com/gpumem: 8192`) |
| Scale | scale-to-zero (`minReplicas: 0`, 10m retention) |
| Weights | PVC `sapbert-data` (RWX, nfs-models; migrated from RWO) |
