# ESM-2 3B (facebook/esm2_t36_3B_UR50D)

Meta's **largest ESM-2** protein language model (3B params, 36 layers) — state-of-the-art
**2560-dim mean-pooled per-protein embeddings** for structure/function/variant prediction.
Custom FastAPI/transformers server on a HAMi GPU slice (20 GiB, fp16), scale-to-zero. Slow cold
start (~3-6 min). OpenAI-compliant `/v1/embeddings` (batch + usage).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + model (nfs-client)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

The 9-check protein-embedding battery runs inside the gateway pod (first call wakes a 3B GPU model —
cold start ~3-6 min):

```bash
cat models/esm2-3b/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **7 PASS / 2 EXP / 0 FAIL** — dim 2560, batch, model-echo, usage,
distinctness, encoding_format, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` EsmModel (GPU, fp16) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped; `input`), health `/health` |
| Embedding dim | 2560 (mean-pooled over residues) |
| Max input | 1022 residues |
| Parameters | 3B (36 layers) |
| GPU | HAMi slice 20 GiB (`nvidia.com/gpumem: 20480`) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `esm2-3b-data` (RWX, nfs-client) |
