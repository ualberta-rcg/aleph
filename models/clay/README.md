# Clay (made-with-clay/Clay)

Clay Foundation Model v1.5 (large, ~330M) — a Masked Autoencoder for multi-band satellite
imagery. The encoder produces a **CLS embedding** from an any-band image cube with per-band
wavelengths (µm), ground sampling distance, and optional geolocation/time metadata. Use cases:
land classification, change detection, environmental monitoring.

Custom FastAPI/lightning server on CPU, scale-to-zero, venv-on-PVC.

**Non-text domain model**: image+metadata input — does **not** expose OpenAI `/v1/embeddings`.
Serves its domain endpoint `POST /v1/science/embed`.

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + checkpoint + repo (nfs-client) — cp-migrated from old RWO
kubectl apply -f inferenceservice.yaml # ConfigMap (server.py) + ISVC, CPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/clay/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **6 PASS / 0 FAIL** — dim (read from response), non-zero, distinctness,
deterministic, model-echo, malformed.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + lightning `claymodel` encoder (CPU) |
| Endpoint | `POST /v1/science/embed` (domain; pixels+waves, not OpenAI text) |
| Embedding dim | CLS (large encoder; read from `embedding_dim` in response) |
| Input | `pixels` [bands,H,W], `waves` µm, `gsd` m, optional lat/lon/time |
| Parameters | ~330M (ViT-Large encoder) |
| GPU | none (CPU) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| PVC | `clay-data-rwx` (RWX, nfs-client, 8Gi) — venv + weights + repo |
