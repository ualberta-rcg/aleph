# DNABERT-S (zhihan1996/DNABERT-S)

Species-aware DNA foundation model — builds on DNABERT-2 with Manifold Instance Mixup (MI-Mix) +
Curriculum Contrastive Learning (C2LR). Produces **768-dim species-discriminative DNA embeddings**
for metagenomics, species identification, and phylogenomics. Custom FastAPI/transformers server,
CPU-only (flash-attention issues on L40S), scale-to-zero.

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + model (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/dnabert-s/test.py

# Or inside the gateway pod (no auth)
cat models/dnabert-s/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 768, batch, model-echo, usage,
distinctness, encoding_format, truncation, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` (CPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI; + `/v1/science/predict` secondary) |
| Embedding dim | 768 (species-discriminative) |
| Max input | 512 tokens |
| Parameters | ~117M |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `dnabert-s-data` (RWX, nfs-models) |
