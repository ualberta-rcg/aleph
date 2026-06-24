# ESM-2 35M (facebook/esm2_t12_35M_UR50D)

Meta's smallest ESM-2 protein language model (12 layers) — **480-dim mean-pooled per-protein
embeddings** of amino-acid sequences (up to 1024 residues). Fastest ESM-2 variant. Custom
FastAPI/transformers server on a HAMi GPU slice (fp16), scale-to-zero.

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + HF cache (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/esm2-35m/test.py

# Or inside the gateway pod (no auth)
cat models/esm2-35m/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 480, batch, model-echo, usage,
distinctness, encoding_format, truncation, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` EsmModel (GPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped; `input`/`sequences`), health `/health` |
| Embedding dim | 480 (mean-pooled over residues) |
| Max input | 1024 residues |
| Parameters | 35M (12 layers) |
| GPU | HAMi slice 3 GiB (`nvidia.com/gpumem: 3072`) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `esm2-35m-data` (RWX, nfs-models; loads model from HF hub, cache on PVC) |
