# Bio_ClinicalBERT (emilyalsentzer/Bio_ClinicalBERT)

BERT initialized from BioBERT and trained on **MIMIC-III clinical notes** — 768-dim mean-pooled
embeddings for clinical NLP (de-identification context, clinical NER, similarity/retrieval).
Custom FastAPI/transformers server, CPU-only, scale-to-zero.

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX weights + venv (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/clinicalbert/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
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
| Parameters | 110M (BERT-base) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `clinicalbert-data` (RWX, nfs-models) |
