# Clinical-Longformer (yikuan8/Clinical-Longformer)

Longformer-base pre-trained on MIMIC-III clinical notes — **768-dim [CLS]-pooled embeddings of
long clinical documents (up to 4096 tokens)** with global attention on CLS. Superior to
ClinicalBERT for long texts. Custom FastAPI/transformers server on a HAMi GPU slice, scale-to-zero.
Serves the standard OpenAI `/v1/embeddings` (legacy `/v1/science/embed` kept).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + model (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/clinical-longformer/test.py

# Or inside the gateway pod (no auth)
cat models/clinical-longformer/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 768, batch, model-echo, usage,
distinctness, long-doc (~2000 tok), encoding_format, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` LongformerModel (GPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI; + `/v1/science/embed` secondary) |
| Embedding dim | 768 ([CLS]-pooled, global attention on CLS) |
| Max input | 4096 tokens |
| Parameters | 149M (Longformer-base) |
| GPU | HAMi slice 10 GiB (`nvidia.com/gpumem: 10240`) |
| Scale | scale-to-zero (`minReplicas: 0`, 10m retention) |
| Weights | PVC `clinical-longformer-data` (RWX, nfs-models; migrated from RWO) |
