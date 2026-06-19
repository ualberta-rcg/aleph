# Ancient Greek BERT (pranaydeeps/Ancient-Greek-BERT)

BERT-base pre-trained on Ancient Greek texts for Digital Humanities / classical studies —
**768-dim [CLS]-pooled embeddings** of Ancient/Byzantine Greek text (philological analysis,
authorship attribution, textual similarity). Custom FastAPI/transformers server on a HAMi GPU
slice, scale-to-zero. Serves the standard OpenAI `/v1/embeddings` (legacy `/v1/science/embed` kept).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + model (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/ancient-greek-bert/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 768, batch, model-echo, usage,
distinctness, encoding_format, truncation, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` AutoModel (GPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI; + `/v1/science/embed` secondary) |
| Embedding dim | 768 ([CLS]-pooled) |
| Max input | 512 tokens |
| Parameters | 110M (BERT) |
| GPU | HAMi sub-GPU slice |
| Scale | scale-to-zero (`minReplicas: 0`, 10m retention) |
| Weights | PVC `ancient-greek-bert-data` (RWX, nfs-models; migrated from RWO) |
