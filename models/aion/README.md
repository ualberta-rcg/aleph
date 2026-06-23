# AION-base (polymathic-ai/aion-base)

AION-base (300M, Polymathic AI) — an astronomical multimodal foundation model trained on 39
astronomical data types across DESI Legacy Survey, SDSS, Gaia, and HSC Wide. A CodecManager
encodes typed modality objects (multiband images, spectra, photometry, catalogs) into a shared
**768-dim object-level embedding** (mean-pool over tokens).

Custom FastAPI/polymathic-aion server on CPU, scale-to-zero, venv-on-PVC.

**Non-text domain model**: astronomical-array input — does **not** expose OpenAI `/v1/embeddings`.
Serves its domain endpoint `POST /v1/science/embed`.

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + weights + warmed HF cache (nfs-models) — cp-migrated from old RWO
kubectl apply -f inferenceservice.yaml # ConfigMap (server.py) + ISVC, CPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/aion/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **6 PASS / 0 FAIL** — dim 768, non-zero, distinctness, deterministic,
model-echo, photometry modality, malformed.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `polymathic-aion` (AION + CodecManager) (CPU) |
| Endpoint | `POST /v1/science/embed` (domain; image/photometry, not OpenAI text) |
| Embedding dim | 768 (object-level mean-pool over tokens) |
| Modalities | `legacy_image` (4-band 96×96), `photometry` (scalars) |
| Parameters | 300M |
| GPU | none (CPU) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| PVC | `aion-data-rwx` (RWX, nfs-models, 8Gi) — venv + weights + cache |
