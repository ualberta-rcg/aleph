# Granite Geospatial Ocean — Sentinel-3 Ocean Color Foundation Model

## Source
- HuggingFace: https://huggingface.co/ibm-granite/granite-geospatial-ocean
- License: Apache 2.0

## Deployment Summary
- **Model**: Granite Geospatial Ocean (ViT MAE)
- **GPU**: 1x L40S (dedicated)
- **PVC**: granite-geospatial-ocean-data (inline in ISVC)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: No (pip install on every start)

## API
- `POST /v1/science/embed` — Sentinel-3 imagery to ocean embeddings
- Input: (C=16, H=42, W=42) Sentinel-3 bands
- Output: (N, 768) patch embeddings
- Demo mode: returns synthetic embeddings

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + init container
- `details.yaml` — model metadata ConfigMap
- No separate pvc.yaml

## Dependencies
- terratorch (prithvi_eo_v2_300 backbone)
- torch + torchvision (CUDA 12.6)
- fastapi, uvicorn, huggingface_hub

## Audit Notes
- Uses prithvi_eo_v2_300 backbone adapted for 16-channel ocean input
- State dict key prefix stripping: model.encoder., model., encoder., backbone.
- Falls back to raw state dict demo mode if backbone fails
- Sentinel file: /data/.granite-ocean-ready-v1
- 16 Sentinel-3 bands: OL1-OL12, OL16, OL17, OL18, OL21 + SLSTR SST
- Image size: 42x42 patches

## Update Reminder
- Monitor ibm-granite for updated checkpoints
- Consider adding chlorophyll/water quality prediction heads
- Could add SST anomaly detection endpoint
