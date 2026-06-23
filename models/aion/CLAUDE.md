# aion — AION-base astronomical multimodal embeddings

AION-base (300M, Polymathic AI) — astronomical multimodal foundation model. CodecManager encodes
typed modality objects (multiband images, spectra, photometry, catalogs) into a shared **768-dim**
object-level embedding (mean-pool over tokens). Trained on 39 data types across DESI/SDSS/Gaia/HSC.

## Source
- HuggingFace: https://huggingface.co/polymathic-ai/aion-base
- License: MIT

## API — `POST /v1/science/embed` (NON-OpenAI domain endpoint)
Astronomical-array input → does NOT expose OpenAI `/v1/embeddings`. Body needs `"model": "aion"`:
- `{"model":"aion", "modality":"legacy_image", "image":[[band,H,W]]}` → 768-dim (4-band 96×96; resized)
- `{"model":"aion", "modality":"photometry", "photometry":[scalars]}` → 768-dim
- Returns `{"embedding":..., "embeddings":...(alias), "dims":768, "model":"aion-base", "modality":...}`.
  (`embeddings` alias added 2026-06-19 for cross-embedder consistency.)
- `GET /v1/science/info` → model metadata.

## Deployment
- **CPU-only** (300M encoder-decoder; runs on CPU).
- **PVC**: `aion-data-rwx` — **ReadWriteMany**, nfs-models, 8 Gi (`pvc.yaml`). Migrated RWO→RWX
  2026-06-19 via **cp-from-RWO** (venv + weights + warmed HF cache preserved; old `aion-data`
  deleted). Split out of the ISVC (was inline + RWO).
- **Venv-on-PVC**: init installs torch+torchvision+`polymathic-aion` into `/data/venv` and WARMS
  the model+codecs (image + photometry) so weights land in `/data/hf_cache`; runtime runs
  `HF_HUB_OFFLINE=1` from that cache. Marker `/data/hf_cache/.aion-warm2` gates re-warm.
- **Scale-to-zero**: minReplicas 0, 15m retention.

## Key files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC (PVC split to `pvc.yaml`)
- `details.yaml` — v2 card (Template C)
- `pvc.yaml` — RWX PVC
- `test.py` — 6-case gateway battery (dim 768 / non-zero / distinctness / deterministic / echo / photometry / malformed)

## Notes (hard-won)
- PyPI package `polymathic-aion`; **import name is `aion`** (NOT `polymathic_aion`).
- AION has no HF text tokenizer — it needs **codec-tokenized modality objects**
  (`aion.modalities.LegacySurveyImage`, etc.), not raw floats.
- Runtime has NO HF egress; the init warms weights into `/data/hf_cache` so the runtime is offline.
- Images resized to 96×96 (codec needs 576 tokens); embedding mean-pooled over tokens → 768-dim.

## Update reminder
- Bump `.aion-warm2` to add modality codecs (spectra, HSC images) — also add a `_build_modality` branch.
