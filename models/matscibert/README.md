# MatSciBERT (m3rg-iitd/matscibert)

BERT fine-tuned on ~1.2M materials-science abstracts — **768-dim [CLS]-pooled embeddings** of
materials text (outperforms SciBERT/BERT on MatSci NLP). Also supports masked-token prediction.
Custom FastAPI/transformers server on a HAMi GPU slice, scale-to-zero.

Serves the **standard OpenAI `/v1/embeddings`** (primary); `/v1/science/embed` and
`/v1/science/predict` are kept as secondary endpoints.

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX weights + venv (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/matscibert/test.py

# Or inside the gateway pod (no auth)
cat models/matscibert/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 768, batch, model-echo, usage,
distinctness, encoding_format, truncation, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` AutoModel (GPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI; + `/v1/science/embed`, `/v1/science/predict` secondary) |
| Embedding dim | 768 ([CLS]-pooled) |
| Max input | 512 tokens |
| Parameters | 110M (BERT) |
| GPU | HAMi slice 3 GiB (`nvidia.com/gpumem: 3072`) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `matscibert-data` (RWX, nfs-models, 15Gi) |
