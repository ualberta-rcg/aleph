# aion Notes

## Purpose
AION-base 300M astronomical multimodal foundation model (Polymathic AI). Produces 768-dim
modality-agnostic embeddings from astronomical data (images, spectra, photometry, catalogs).

## Runtime
- Custom FastAPI server (ConfigMap `aion-server`), venv-on-PVC. CPU-only.
- Package: `polymathic-aion` (PyPI) — **import name is `aion`** (NOT `polymathic_aion`).
- Real API: `AION.from_pretrained('polymathic-ai/aion-base')` + `CodecManager` + typed
  modality objects from `aion.modalities` (e.g. `LegacySurveyImage`, `LegacySurveyFluxG`).

## Why it was broken before (2026-06-05 deep-fix)
- "READY" but model never loaded: `/health` returned 200 while load failed silently.
- Runtime container has NO egress to HF; old server tried to download at startup -> failed.
- Old server imported `polymathic_aion` (wrong) and passed raw floats as `inputs_embeds`
  (AION has no HF text tokenizer; it needs codec-tokenized modality objects).

## The fix
- Init container (has egress) installs torch+torchvision+polymathic-aion, then WARMS the
  model + codecs by running a real encode (image + photometry) so weights land in
  `/data/hf_cache`. Runtime then runs `HF_HUB_OFFLINE=1` from that cache.
- Server constructs typed modalities; images resized to 96x96 (codec needs 576 tokens);
  embeddings mean-pooled over tokens -> 768-dim.
- Marker `/data/hf_cache/.aion-warm2` gates re-warm; bump it to add more modality codecs.

## Extending modalities
To support spectra (DESI/SDSS) or HSC images, add those modality encodes to the init warmup
(so their codecs are cached) and a branch in `_build_modality`.

## Validation
See [TEST.md](TEST.md). legacy_image + photometry verified -> 768-dim.
