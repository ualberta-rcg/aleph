# Prithvi-EO-2.0 — IBM/NASA Earth Observation Foundation Model

## Source
- HuggingFace: https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-300M
- License: Apache 2.0

## Deployment Summary
- **Model**: Prithvi-EO-2.0-300M (300M params)
- **GPU**: 1x L40S (shared)
- **PVC**: prithvi-eo-data (inline in ISVC)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/embed` — 6-band satellite imagery to patch embeddings
- Input: (T, H, W, 6) or (H, W, 6) auto-replicated to 4 time steps
- Output: (num_patches, 1024) embeddings + shape
- Recommended: 4 time steps x 224x224 pixels

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + init container
- `details.yaml` — model metadata ConfigMap
- No separate pvc.yaml

## Dependencies
- terratorch (for prithvi_eo_v2_300 backbone)
- torch (CUDA 12.6)
- huggingface_hub, fastapi, uvicorn

## Audit Notes
- Uses terratorch's prithvi_eo_v2_300 backbone builder
- Encoder-only weights loaded (decoder keys stripped)
- Sentinel file: /data/venv/.prithvi-eo-ready-v3
- Single-frame input auto-replicated to 4 time steps
- 6 HLS bands: Blue, Green, Red, NIR, SWIR, SWIR2

## Update Reminder
- Monitor ibm-nasa-geospatial for 600M variant
- Consider adding fine-tuned classification heads
- Could add flood/fire detection endpoints
