# BrainLM — fMRI Foundation Model

BrainLM (650M, vandijklab, ICLR 2024) — ViT-MAE foundation model for fMRI. Accepts 424-ROI
time-series, converts to a 3-channel 434×434 image (signal + spatial/temporal derivatives), and
runs ViTMAEForPreTraining to extract a **1280-dim latent embedding** per window.

## Source
- HuggingFace: https://huggingface.co/vandijklab/BrainLM
- Paper: ICLR 2024
- License: MIT

## API — `POST /v1/science/embed` (NON-OpenAI domain endpoint, primary)
fMRI-array input → does NOT fit OpenAI `/v1/embeddings` (text-only). Also aliased at `/v1/embeddings`
(secondary). Body needs `"model": "brainlm"`:
- `{"model":"brainlm", "fmri":[[roi1_t1,...],...], "model_size":"650M"}` → shape [424, timepoints] → 1280-dim
- Returns `{"embeddings":[[...1280...]], "model":"brainlm"}`.

## Deployment
- **GPU**: 1× L40S (shared HAMi slice).
- **PVC**: `brainlm-data` — **ReadWriteMany**, nfs-client (already RWX, `pvc.yaml`).
- **Venv-on-PVC**: `/data/venv` (transformers + torch, guarded). Main runs `/data/venv/bin/python`.
- **Scale-to-zero**: minReplicas 0, 15m retention.

## Key files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC
- `details.yaml` — v2 card (Template C)
- `pvc.yaml` — RWX PVC
- `test.py` — 6-case gateway battery (dim 1280 / non-zero / distinctness / deterministic / echo / malformed)

## Notes
- ViT-MAE (a vision model) adapted for fMRI: the server reshapes [424 rois, T] → [3, 434, 434]
  (pad 424→434; channels = signal, spatial-derivative, temporal-derivative). Requires 424 ROIs
  (UK Biobank parcellation); timepoints are padded/truncated to 434 internally.
- Custom weight loading via ViTMAEConfig from config.json.

## Update reminder
- Watch vandijklab/BrainLM for v2 / larger variants (dim may change from 1280).
