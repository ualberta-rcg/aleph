# AstroPT v2.0 — Autoregressive Galaxy Image Transformer

AstroPT v2.0 (95M, UniverseTBD/Smith42) — autoregressive GPT trained on 8.6M galaxy images
(SDSS/DESI). Patchifies a galaxy image and emits **[N, 512] patch latent embeddings** via causal
attention. NOTE: output is patch-level (2D), not a single pooled vector.

## Source
- HuggingFace: https://huggingface.co/Smith42/astroPT_v2.0
- License: MIT

## API — `POST /v1/science/embed` (NON-OpenAI domain endpoint)
Galaxy image input → does NOT expose OpenAI `/v1/embeddings`. Body needs `"model": "astropt"`:
- `{"model":"astropt", "image":[[[R,G,B],...],...]}` → (H,W,3) float [0,1] → patch latents `[N,512]`
- `{"model":"astropt", "demo":true}` → synthetic `[16,512]`
- Returns `{"embeddings":[[...512...],...N], "shape":[N,512], "model":"astropt-095m"}`.

## Deployment
- **GPU**: 1× L40S via HAMi (`nvidia.com/gpumem: 8192`), `nodeSelector: gpu=on`.
- **PVC**: `astropt-data` — **ReadWriteMany**, nfs-models (already RWX, `pvc.yaml`).
- **Venv-on-PVC** (converted 2026-06-19): the old init installed torch into the **ephemeral
  container python** (the `/data` sentinel didn't persist deps), so the main container reinstalled
  cu126 torch on every wake. Now the init builds `/data/venv` on the PVC once (sentinel
  `.astropt-ready-v2`, venv guarded), and the main container runs `/data/venv/bin/python /app/server.py`.
- **Scale-to-zero**: minReplicas 0, 15m retention.

## Key files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + venv-on-PVC init
- `details.yaml` — v2 card (Template C)
- `pvc.yaml` — RWX PVC
- `test.py` — 7-case gateway battery (shape [N,512] / non-zero / distinctness / deterministic / echo / demo / malformed)

## Notes
- Loads via `astropt` package `load_astropt()`. Per-channel mean/std normalization + positional
  encoding for the patch sequence. Snapshot of the full repo downloaded to `/data`.

## Update reminder
- Sentinel v1→v2 bump forced the one-time venv build; on a fresh PVC the venv + weights rebuild.
- Monitor Smith42 for larger variants (dim may change from 512).
