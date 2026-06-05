# EarthPT — Earth Observation Time-Series Foundation Model

## Source
- HuggingFace: https://huggingface.co/Smith42/EarthPT
- Paper: arXiv:2309.06929
- License: MIT

## Deployment Summary
- **Model**: EarthPT 700M (nanoGPT variant)
- **GPU**: 1x L40S (shared)
- **PVC**: earthpt-data (10Gi, NFS, inline in ISVC)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/science/predict` — time-series prediction
- Input: list of 18-float observations (14 spectral + 4 time metadata)
- Output: 14 spectral channel predictions for future steps
- Context window: 256 time steps max

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + init container
- `details.yaml` — model metadata ConfigMap
- No separate pvc.yaml (PVC inline in ISVC)

## Dependencies
- torch (CUDA 12.6)
- huggingface_hub, fastapi, uvicorn, numpy

## Audit Notes
- Full model architecture defined inline in server.py (no external library)
- Sentinel file: /data/venv/.earthpt-v2-ready
- Autoregressive: uses FP16 on GPU for faster inference
- 18 input channels: 14 MODIS spectral bands + 4 time metadata
- Time padding with zeros for autoregressive continuation

## Update Reminder
- Monitor Smith42/EarthPT for new checkpoints
- Consider adding embedding extraction endpoint
- Could extend to other satellite data beyond MODIS
