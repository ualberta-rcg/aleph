# clap Notes

## Purpose
CLAP (laion/larger_clap_general): Contrastive Language-Audio Pretraining. Audio/text
embeddings in a shared 512-dim space (`/v1/embeddings`) and zero-shot audio classification
(`/v1/classify`). CPU.

## Runtime
- Custom FastAPI server (embedded ConfigMap), venv-on-PVC. CPU torch.
- Pinned `torch==2.5.1` (CPU), `transformers==4.46.3`, plus librosa/soundfile.
- HF token via `secretKeyRef`.

## Migration fixes vs 232
- 232 installed **GPU** torch (cu126) but requested no GPU → switched to CPU torch.
- `/v1/classify` used `model.logit_scale` which newer transformers `ClapModel` renamed to
  `logit_scale_a`/`logit_scale_t`. Patched to `logit_scale_a` (with fallback).
- Inline HF token → secretKeyRef; v2 card.

## Input
- `/v1/embeddings`: `{audio: [[float]], texts: [str], sample_rate: 48000}` (either/both).
- `/v1/classify`: `{audio: [[float]], labels: [str], sample_rate: 48000}`.

## Validation
See [TEST.md](TEST.md). text dim=512; 440Hz sine classified as "pure tone" (0.99999).
