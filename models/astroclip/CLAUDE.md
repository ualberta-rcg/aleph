# AstroCLIP — Cross-Modal Galaxy Image + Spectrum CLIP

Real model (not a demo stub since 2026-06-19). Cross-modal contrastive foundation model:
embeds galaxy images (DESI Legacy Survey g,r,z cutouts) and optical spectra (DESI) into a
shared embedding space via a DINOv2 image encoder + masked-modeling spectrum transformer,
aligned by cross-attention CLIP heads.

## Source
- HuggingFace checkpoint: https://huggingface.co/polymathic-ai/astroclip (`astroclip.ckpt`, ~1.7 GB)
- GitHub: https://github.com/PolymathicAI/AstroCLIP  (case-sensitive: `PolymathicAI`, NOT `polymathic-ai`)
- License: MIT

## API — `POST /v1/science/embed` (NON-OpenAI domain endpoint)
AstroCLIP takes **image/spectrum input, not text**, so it does NOT expose OpenAI
`/v1/embeddings`. It stays on its domain endpoint. Body must include `"model": "astroclip"`
(the gateway catch-all requires it):

- `{"model":"astroclip", "image":[[[R,G,B],...],...], "modality":"image"}` → 144×144×3 (g,r,z) → **1024-dim**
- `{"model":"astroclip", "spectrum":[float,...], "modality":"spectrum"}` → wavelength bins → **1024-dim**
- `{"model":"astroclip", "demo":true}` → 1024-dim zero vector (fallback fixture)

## Deployment
- **GPU**: 1× L40S via HAMi (`nvidia.com/gpumem: 10240`), `nodeSelector: gpu=on`
- **PVC**: `astroclip-data` — **ReadWriteMany**, nfs-models, 10 Gi (`pvc.yaml`)
- **Venv-on-PVC**: init builds `/data/venv` once (sentinel `/data/.astroclip-ready-v3`),
  cu126 torch preserved across restarts (venv creation guarded; `--clear` removed).
  Main container runs `/data/venv/bin/python /app/server.py`.
- **Scale-to-zero**: minReplicas 0, 15m idle retention. Cold start ~2-4 min (venv exists;
  checkpoint already on PVC).
- **Self-contained init**: checkpoint download + repo clone + venv are all conditional —
  deleting the PVC and re-applying rebuilds everything.

## Key files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + venv-on-PVC init container
- `details.yaml` — v2 card (Template C)
- `pvc.yaml` — RWX PVC
- `test.py` — 9-case gateway battery (dim, distinctness, cross-modal, deterministic, demo)

## Non-obvious gotchas (hard-won)
1. **Embedding dim is 1024, not 512.** The README/old card say 512; the released
   checkpoint's `ImageHead`/`SpectrumHead` output is empirically 1024. Trust the test.
2. **PyTorch 2.6 `weights_only=True` default.** The Lightning checkpoint stores full
   encoder modules, so it needs `weights_only=False`. Lightning's `pl_load` passes
   `weights_only=True` explicitly → `setdefault` is a no-op. Fix: monkeypatch `torch.load`
   to **force** `weights_only=False` for the process (see `load()` in server.py).
3. **AstroCLIP library batch_size<2 bug.** `astroclip/modules.py` `CrossAttentionHead.forward`
   does `return x, attentions[1]` where `attentions` is the attention *output* `(batch,1,d)`,
   so it indexes the 2nd batch element and raises `IndexError` for `batch_size<2`. Their
   training always uses batches ≥2. Fix in server.py: duplicate single input to a batch of 2
   and return `emb[0]` (cross-attention is per-sample, so `emb[0]` == true single-sample).
4. **`--no-deps` install for both DINOv2 and AstroCLIP** (official). DINOv2 pins torch 2.0
   which would downgrade cu126. Runtime deps must be added explicitly: the `astroclip/__init__.py`
   import chain (`from . import data, models, modules`) pulls in `datasets`, `h5py`,
   `python-dotenv`, `scikit-image`, `matplotlib`, `joblib`, `aiohttp`, `pillow`, `tqdm`, `wandb`.
   Forgetting `datasets` → `No module named 'datasets'` → silent demo fallback.
5. **Correct import**: `from astroclip.models import AstroClipModel` (plural `models`, class
   `AstroClipModel`). The old `from astroclip.model import AstroCLIP` is wrong (no such module).
6. **Lightning `load_from_checkpoint`** reconstructs the encoders from `save_hyperparameters()`
   in the checkpoint — no manual state-dict key patching needed (the old `image_encoder.dino.`
   rewrite was dead code). `strict=False` tolerates drift.

## Update reminder
- Sentinel version bumps (`-v1`→`-v2`→…`) force a re-run of the additive dep installs without
  re-downloading torch (venv guarded).
- Monitor polymathic-ai/astroclip for checkpoint updates; the dim/forward contract may change.
