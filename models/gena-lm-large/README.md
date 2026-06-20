# GENA-LM-large (AIRI-Institute/gena-lm-bert-large-t2t)

BERT-large DNA model trained on the hg38+T2T human genome — **1024-dim [CLS]-pooled DNA
embeddings** for long genomic sequences (max 512 tokens). Custom FastAPI/transformers server on a
HAMi GPU slice, scale-to-zero. Serves the standard OpenAI `/v1/embeddings` (`/v1/science/embed` kept).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + model (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/gena-lm-large/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **6 PASS / 3 EXP / 0 FAIL** — dim 1024, batch, model-echo, usage,
truncation, guardrails, catalog. (distinctness EXP — DNA BERT-large CLS on short sequences is
borderline, cos~1.0.)

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` AutoModel (GPU, trust_remote_code) |
| Endpoint | `POST /v1/embeddings` (OpenAI; + `/v1/science/embed` secondary) |
| Embedding dim | 1024 ([CLS]-pooled) |
| Max input | 512 tokens |
| Parameters | 340M (BERT-large) |
| GPU | HAMi slice 10 GiB (`nvidia.com/gpumem: 10240`) |
| Scale | scale-to-zero (`minReplicas: 0`, 10m retention) |
| Weights | PVC `gena-lm-large-data` (RWX, nfs-models; migrated from RWO) |
