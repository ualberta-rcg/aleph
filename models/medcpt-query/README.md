# MedCPT-Query-Encoder (ncbi/MedCPT-Query-Encoder)

The **query side** of NCBI's MedCPT — a sentence encoder trained on biomedical relevance
(PubMed clicks + citation context) for biomedical retrieval. Produces **768-dim [CLS] query
embeddings** (max 64 tokens). Pair with `medcpt-article` (the article encoder) for asymmetric
query→article search. Custom FastAPI/transformers server on a HAMi GPU slice, scale-to-zero.
OpenAI-compliant `/v1/embeddings` (batch + usage).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + HF cache (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/medcpt-query/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **7 PASS / 2 EXP / 0 FAIL** — dim 768, batch, model-echo, usage,
distinctness, truncation, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` AutoModel (GPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped; `input`/`queries`), health `/health` |
| Embedding dim | 768 ([CLS]-pooled) |
| Max input | 64 tokens (query encoder — short queries) |
| Parameters | 110M |
| GPU | HAMi slice 8 GiB (`nvidia.com/gpumem: 8192`) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `medcpt-query-data` (RWX, nfs-models; migrated from RWO) |
