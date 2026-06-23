# Prithvi-EO-2.0-300M (ibm-nasa-geospatial/Prithvi-EO-2.0-300M)

Prithvi-EO-2.0-300M (IBM/NASA/JSC, 300M) — an earth-observation foundation model: a 3D ViT MAE
pretrained on NASA HLS V2 satellite imagery. Accepts 6-band multispectral data (Blue, Green, Red,
NIR, SWIR, SWIR2) with multi-temporal input, and `forward_features` extracts a **1024-dim CLS
embedding** (+ per-patch features). Use cases: land classification, change detection, flood/fire
detection, environmental monitoring.

Custom FastAPI/terratorch server on a HAMi GPU slice, scale-to-zero, venv-on-PVC.

**Non-text domain model**: image-cube input — does **not** expose OpenAI `/v1/embeddings`.
Serves `POST /v1/science/embed` (with `/v1/embed` as a secondary alias).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + weights (nfs-models, already RWX)
kubectl apply -f inferenceservice.yaml # ConfigMap (server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/prithvi-eo/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **6 PASS / 0 FAIL** — dim 1024, non-zero, distinctness, deterministic,
model-echo, malformed.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + terratorch `prithvi_eo_v2_300` backbone (GPU) |
| Endpoint | `POST /v1/science/embed` (domain; 6-band cube; `/v1/embed` secondary) |
| Embedding dim | 1024 (CLS via forward_features) |
| Input | `image` (H,W,6) or (T,H,W,6) — 6 HLS bands (replicated to T=1 if 3D) |
| Parameters | 300M |
| GPU | HAMi L40S slice |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| PVC | `prithvi-eo-data` (RWX, nfs-models) — venv + weights |
