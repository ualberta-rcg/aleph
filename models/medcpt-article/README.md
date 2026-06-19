# MedCPT-Article-Encoder (ncbi/MedCPT-Article-Encoder)

The **article/document side** of NCBI's MedCPT — trained on biomedical relevance (PubMed clicks +
citation context) for biomedical retrieval. Produces **768-dim [CLS] embeddings** of medical
documents (title+abstract, max 512 tokens). Pair with `medcpt-query` (the query encoder) for
asymmetric query→article search. Custom FastAPI/transformers server on a HAMi GPU slice, scale-to-zero.
OpenAI-compliant `/v1/embeddings` (batch + usage).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + HF cache (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/medcpt-article/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **7 PASS / 2 EXP / 0 FAIL** — dim 768, batch, model-echo, usage,
distinctness, truncation, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` AutoModel (GPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped; `input`/`articles`), health `/health` |
| Embedding dim | 768 ([CLS]-pooled) |
| Max input | 512 tokens (title+abstract) |
| Parameters | 110M |
| GPU | HAMi slice 8 GiB (`nvidia.com/gpumem: 8192`) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `medcpt-article-data` (RWX, nfs-models; migrated from RWO) |
