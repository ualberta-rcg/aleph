# SaProt 650M (westlake-repl/SaProt_650M_AF2)

**Structure-aware** protein language model — trained on a fused amino-acid + foldseek-3Di
structure vocabulary, so it captures both sequence and structure (ESM-2 650M backbone).
**1280-dim mean-pooled** embeddings for function/structure/variant tasks. Custom FastAPI/
transformers server on a HAMi GPU slice, scale-to-zero. OpenAI-compliant `/v1/embeddings`.

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + model (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/saprot-650m/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 1280, batch, model-echo, usage,
distinctness, encoding_format, truncation, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` EsmModel (GPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped; `input`/`sequences`), health `/health` |
| Embedding dim | 1280 (mean-pooled, structure-aware) |
| Max input | 1024 residues |
| Parameters | 650M (ESM-2 backbone, AA+3Di vocab) |
| GPU | HAMi slice 10 GiB (`nvidia.com/gpumem: 10240`) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `saprot-650m-data` (RWX, nfs-models; migrated from RWO) |
