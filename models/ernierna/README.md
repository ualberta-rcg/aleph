# ERNIE-RNA (multimolecule/ernierna)

Structure-aware RNA foundation model — pre-trained on RNAcentral with structure-aware objectives;
outperforms RNA-FM on structure-prediction tasks. **768-dim mean-pooled RNA embeddings** (max 1024
tokens). Custom FastAPI server (multimolecule ErnieRnaModel) on a HAMi GPU slice, scale-to-zero.
Serves the standard OpenAI `/v1/embeddings` (`/v1/science/embed` kept).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + model (nfs-models)
kubectl apply -f inferenceservice.yaml # custom FastAPI server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/ernierna/test.py

# Or inside the gateway pod (no auth)
cat models/ernierna/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **6 PASS / 2 EXP / 0 FAIL** — dim 768, batch, model-echo, usage,
distinctness, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `multimolecule` ErnieRnaModel (GPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI; + `/v1/science/embed` secondary) |
| Embedding dim | 768 (mean-pooled) |
| Max input | 1024 tokens |
| Parameters | ~86M |
| GPU | HAMi slice 10 GiB (`nvidia.com/gpumem: 10240`) |
| Scale | scale-to-zero (`minReplicas: 0`, 10m retention) |
| Weights | PVC `ernierna-data` (RWX, nfs-models; migrated from RWO) |
