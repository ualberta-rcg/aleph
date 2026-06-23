# HyenaDNA medium-160k (LongSafari/hyenadna-medium-160k-seqlen-hf)

Long-range **DNA embedding model** — state-space (Hyena operators, no attention, sub-quadratic) for
up to 160K base pairs. This deployment truncates to 8192 bp and produces **256-dim mean-pooled
embeddings** for regulatory genomics, promoter prediction, chromatin accessibility. Custom
FastAPI/transformers server, CPU-only, scale-to-zero. OpenAI-compliant `/v1/embeddings` (batch + usage).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + model (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/hyenadna/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **7 PASS / 2 EXP / 0 FAIL** — dim 256, batch, model-echo, usage,
distinctness, long-seq (~4000 bp), guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` AutoModel (CPU, trust_remote_code) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped; `input`), health `/health` |
| Embedding dim | 256 (mean-pooled) |
| Max input | 8192 bp (model supports 160K) |
| Parameters | 6.5M (state-space / Hyena) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `hyenadna-data` (RWX, nfs-models) |
