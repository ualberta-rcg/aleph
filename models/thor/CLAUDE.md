# THOR 1.0-base — Multi-Sensor Geospatial Foundation Model

## Source
- HuggingFace: https://huggingface.co/FM4CS/THOR-1.0-base
- Extension: https://github.com/FM4CS/thor_terratorch_ext
- License: Apache 2.0

## Deployment Summary
- **Model**: THOR 1.0-base (FlexiViT-Base, ~400MB)
- **GPU**: 1x L40S (dedicated)
- **PVC**: thor-data (4Gi, NFS ReadWriteMany)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: No (pip install on every start)

## API
- `POST /v1/science/embed` — satellite image to patch embeddings
- Input: (C, H, W) image + band names + patch_size + ground_cover
- Output: (N, 768) patch embeddings
- Supports Sentinel-1 SAR, Sentinel-2 MSI, Sentinel-3 OLCI/SLSTR
- Demo mode: `{"demo": true}` returns synthetic embeddings

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + init container
- `pvc.yaml` — thor-data PVC (4Gi NFS)
- `details.yaml` — model metadata ConfigMap

## Dependencies
- terratorch (TerraTorch framework)
- thor_terratorch_ext (THOR backbone registration)
- torch (CUDA 12.6)
- fastapi, uvicorn, huggingface_hub

## Audit Notes
- thor_terratorch_ext not on PyPI — cloned from GitHub to /data/src
- Falls back to raw checkpoint demo mode if extension unavailable
- Sentinel file: /data/.thor-ready-v1
- Supports multiple Sentinel sensors (1, 2, 3)
- Flexible patch sizes for different resolutions

## Update Reminder
- Monitor FM4CS/THOR for new model variants
- Watch for thor_terratorch_ext PyPI release
- Consider migrating to venv-on-PVC pattern
- Could expand to support classification fine-tuning heads
