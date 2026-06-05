# AstroPT v2.0 — Autoregressive Galaxy Image Transformer

## Source
- HuggingFace: https://huggingface.co/Smith42/astroPT_v2.0
- License: MIT

## Deployment Summary
- **Model**: AstroPT v2.0 (095M params)
- **GPU**: 1x L40S (dedicated)
- **PVC**: astropt-data (inline in ISVC)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: No (pip install on every start)

## API
- `POST /v1/science/embed` — galaxy image to latent embeddings
- Input: (H, W, 3) or (3, H, W) RGB galaxy image float [0,1]
- Output: (num_patches, 512) latent embeddings
- Demo mode: `{"demo": true}` returns synthetic (16, 512) embeddings

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + init container
- `details.yaml` — model metadata ConfigMap
- No separate pvc.yaml

## Dependencies
- astropt (pip package)
- torch + torchvision (CUDA 12.6)
- fastapi, uvicorn, huggingface_hub

## Audit Notes
- Uses official load_astropt() API for model loading
- Per-channel normalization (mean/std) applied to input images
- Positional encoding generated for patch sequence
- Sentinel file: /data/.astropt-ready-v1
- Snapshot download of full repo to PVC

## Update Reminder
- Monitor Smith42/astroPT_v2.0 for larger model variants
- Consider adding classification/regression heads for redshift
- Add separate pvc.yaml for consistency
