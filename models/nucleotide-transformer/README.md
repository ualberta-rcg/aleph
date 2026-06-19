# Nucleotide Transformer v2 500M (InstaDeepAI/nucleotide-transformer-v2-500m-multi-species)

InstaDeepAI's **Nucleotide Transformer** — a DNA foundation model trained across multiple species
(500M params). Produces **1024-dim mean-pooled DNA embeddings** for genomics tasks. Custom
FastAPI/transformers server on a HAMi GPU slice, scale-to-zero. OpenAI-compliant `/v1/embeddings`.

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + HF cache (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/nucleotide-transformer/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **7 PASS / 2 EXP / 0 FAIL** — dim 1024, batch, model-echo, usage,
distinctness, truncation, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` EsmModel (GPU, trust_remote_code) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped; `input`/`sequences`), health `/health` |
| Embedding dim | 1024 (mean-pooled) |
| Max input | 2048 tokens |
| Parameters | 500M |
| GPU | HAMi sub-GPU slice (`nvidia.com/gpumem: 4096`) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `nucleotide-transformer-data` (RWX, nfs-models, 15Gi) |
