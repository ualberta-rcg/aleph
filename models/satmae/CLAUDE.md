# SatMAE — Masked Autoencoder for Satellite Imagery

SatMAE (MVRL) — ViT-Large Masked Autoencoder pretrained on fMoW satellite imagery.
Zero-mask `forward_encoder` → **1024-dim [CLS] embedding** of an RGB satellite image patch.

## Source
- HuggingFace: https://huggingface.co/MVRL/satmae-vitlarge-fmow-pretrain-800
- License: Apache-2.0

## API — `POST /v1/science/embed` (NON-OpenAI domain endpoint)
Image input, not text → does NOT expose OpenAI `/v1/embeddings`. Body needs `"model": "satmae"`:
- `{"model":"satmae", "image":[[[R,G,B],...],...]}` → HxW RGB (0-255; auto-resized 224×224, fMoW-normalized) → 1024-dim
- Returns `{"embeddings":..., "cls_embedding":..., "patch_embeddings":..., "dim":1024, "model":"satmae"}`.
  (`embeddings` is an alias of `cls_embedding`, added 2026-06-19 for cross-embedder consistency.)

## Deployment
- **CPU-only** (~300M ViT-Large; runs on CPU, ~seconds/image).
- **PVC**: `satmae-data-rwx` — **ReadWriteMany**, nfs-models, 5 Gi (`pvc.yaml`). Migrated
  RWO→RWX 2026-06-19 via **cp-from-RWO** (preserved the venv + HF snapshot; old `satmae-data`
  deleted). Split out of the ISVC (was inline + RWO).
- **Venv-on-PVC**: `/data/venv` (torch+torchvision+safetensors+timm, guarded). Main container
  runs `/data/venv/bin/python /app/server.py`. `HF_HUB_OFFLINE=1`.
- **Scale-to-zero**: minReplicas 0, 15m retention.

## Key files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC (PVC split to `pvc.yaml`)
- `details.yaml` — v2 card (Template C)
- `pvc.yaml` — RWX PVC
- `test.py` — 6-case gateway battery (dim 1024 / non-zero / distinctness / deterministic / echo / malformed)

## Notes
- `MaskedAutoencoderViT.from_pretrained(MODEL_DIR)` — the model code lives in the HF snapshot
  (`sys.path.insert(0, MODEL_DIR); from model import MaskedAutoencoderViT`), loaded offline.
- fMoW normalization: mean=[0.4182, 0.4215, 0.3991], std=[0.2877, 0.2754, 0.2764]; mask_ratio=0.
- Auto-resizes non-224×224 inputs via bilinear interpolation.

## Update reminder
- Monitor MVRL for multi-spectral / temporal SatMAE variants.
