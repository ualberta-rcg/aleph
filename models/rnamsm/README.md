# RNA-MSM (multimolecule/rnamsm)

RNA language model using a **multiple-sequence-alignment (MSA) transformer** approach, trained on
Rfam. **768-dim mean-pooled RNA embeddings** that capture MSA context for secondary-structure
prediction (max 1024 tokens). Custom FastAPI server (multimolecule RnaMsmModel) on a HAMi GPU slice,
scale-to-zero. Serves the standard OpenAI `/v1/embeddings` (`/v1/science/embed` kept).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + model (nfs-models)
kubectl apply -f inferenceservice.yaml # custom FastAPI server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/rnamsm/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **6 PASS / 2 EXP / 0 FAIL** — dim 768, batch, model-echo, usage,
distinctness, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `multimolecule` RnaMsmModel (GPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI; + `/v1/science/embed` secondary) |
| Embedding dim | 768 (mean-pooled) |
| Max input | 1024 tokens |
| Parameters | ~96M |
| GPU | HAMi slice 8 GiB (`nvidia.com/gpumem: 8192`) |
| Scale | scale-to-zero (`minReplicas: 0`, 10m retention) |
| Weights | PVC `rnamsm-data` (RWX, nfs-models; migrated from RWO) |
