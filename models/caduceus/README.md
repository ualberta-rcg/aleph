# Caduceus-PS (kuleshov-group/caduceus-ps_seqlen-131k_d_model-256_n_layer-16)

Bidirectional **Mamba state-space DNA model** with Reverse-Complement Permutation Symmetry (RCPS).
Long-context (131k native; deployed max 8192). Produces **256-dim mean-pooled DNA embeddings**
(forward + reverse-complement averaged for RC-invariance). float32 (SSMs are precision-sensitive).
Custom FastAPI/transformers server on a HAMi GPU slice, scale-to-zero. OpenAI-compliant `/v1/embeddings`.

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + weights (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/caduceus/test.py

# Or inside the gateway pod (no auth)
cat models/caduceus/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **7 PASS / 2 EXP / 0 FAIL** — dim 256, batch, model-echo, usage,
distinctness, truncation, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` AutoModel (GPU, trust_remote_code, mamba-ssm) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped; `input`/`sequences`), health `/health` |
| Embedding dim | 256 (RCPS fwd+rc averaged, mean-pooled) |
| Max input | 8192 tokens |
| Precision | fp32 (SSM precision-sensitive) |
| GPU | HAMi slice 10 GiB (`nvidia.com/gpumem: 10240`) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `caduceus-data` (RWX, nfs-models, 10Gi) |
