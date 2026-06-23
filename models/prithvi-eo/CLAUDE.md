# Prithvi-EO-2.0 — IBM/NASA Earth Observation Foundation Model

Prithvi-EO-2.0-300M (IBM/NASA/JSC, 300M) — 3D ViT MAE pretrained on NASA HLS V2 satellite imagery.
`forward_features` extracts a **1024-dim CLS embedding** (+ per-patch features) from 6-band
multi-temporal data (Blue/Green/Red/NIR/SWIR/SWIR2).

## Source
- HuggingFace: https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-300M
- License: Apache-2.0

## API — `POST /v1/science/embed` (NON-OpenAI domain endpoint, primary)
Image-cube input → does NOT expose OpenAI `/v1/embeddings`. `/v1/embed` kept as secondary.
Body needs `"model": "prithvi-eo"`:
- `{"model":"prithvi-eo", "image":[[[band,...],...],...]}` shape (H,W,6) or (T,H,W,6); (H,W,6) replicated to T=1 → 1024-dim
- Returns `{"embeddings":..., "cls_embedding":...(alias), "cls_embedding_dim":1024, "num_patches":..., ...}`.
  (Full CLS vector returned 2026-06-19 — the old server returned only a 10-element summary "to avoid huge payloads"; 1024 floats ~8KB is fine.)

## Deployment
- **GPU**: 1× L40S (shared HAMi slice).
- **PVC**: `prithvi-eo-data` — **ReadWriteMany**, nfs-models (already RWX, `pvc.yaml`).
- **Venv-on-PVC**: `/data/venv` (terratorch + torch cu126, guarded, sentinel `.prithvi-eo-ready-v3`).
- **Scale-to-zero**: minReplicas 0, 15m retention.

## Key files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC
- `details.yaml` — v2 card (Template C)
- `pvc.yaml` — RWX PVC
- `test.py` — 6-case gateway battery (dim 1024 / non-zero / distinctness / deterministic / echo / malformed)

## Notes
- Loads via terratorch `BACKBONE_REGISTRY` (`prithvi_eo_v2_300`); encoder-only weights (decoder stripped).
- Single-frame (H,W,6) auto-replicated across the temporal axis. 6 HLS bands.

## Update reminder
- Watch ibm-nasa-geospatial for the 600M variant (dim may change).
