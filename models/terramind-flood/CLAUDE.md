# TerraMind-Flood — Multi-Sensor Flood Detection

## Source
- HuggingFace: https://huggingface.co/ibm-esa-geospatial/TerraMind-base-Flood
- License: Apache 2.0

## Deployment Summary
- **Model**: TerraMind-1.0-base fine-tuned on ImpactMesh-Flood
- **GPU**: 1x L40S (dedicated)
- **PVC**: terramind-flood-data (4Gi, NFS ReadWriteMany)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: No (pip install on every start)

## API
- `POST /v1/science/classify` — multi-sensor stack to flood segmentation
- Input: S2L2A (12 bands), S1RTC (2 bands), DEM (1 band), 4 time steps, 256x256
- Output: binary flood mask + probability map + area percentage
- Demo mode: returns synthetic flood mask

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + init container
- `pvc.yaml` — terramind-flood-data PVC (4Gi NFS)
- `details.yaml` — model metadata ConfigMap

## Dependencies
- terratorch==1.2.1 (pinned version)
- torch + torchvision (CUDA 12.6)
- fastapi, uvicorn, huggingface_hub

## Audit Notes
- Currently in demo mode — config version mismatch with terratorch
- State dict inspected but not loaded into model
- Pinned to terratorch==1.2.1 for compatibility
- Multi-sensor: combines optical (S2), SAR (S1), and elevation (DEM)
- Sentinel file: /data/.terramind-flood-ready-v1
- Binary segmentation: flood vs no-flood

## Update Reminder
- Fix terratorch config version mismatch for real inference
- Monitor ibm-esa-geospatial for updated models
- Consider adding damage assessment endpoint
- Could extend to other disaster types (fire, landslide)
