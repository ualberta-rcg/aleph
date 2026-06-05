# Naturecode Earth — Forest Monitoring Foundation Model

## Source
- HuggingFace: https://huggingface.co/naturecodeproject/earth
- License: Apache 2.0

## Deployment Summary
- **Model**: Naturecode Earth (10.9M, nano variant)
- **GPU**: 1x L40S (dedicated)
- **PVC**: naturecode-earth-data (inline in ISVC)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: No (pip install on every start)

## API
- `POST /v1/science/predict` — Sentinel-2 time-series to forest analysis
- Input: 4 quarterly Sentinel-2 composites (6 bands, 64x64) + location + timestamps
- Output: segmentation + biomass + soil properties
- Demo mode: returns synthetic forest analysis

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + init container
- `details.yaml` — model metadata ConfigMap
- No separate pvc.yaml

## Dependencies
- torch (CUDA 12.6)
- forestfm (optional, falls back to raw checkpoint)
- fastapi, uvicorn, huggingface_hub

## Audit Notes
- Multi-task model: segmentation + biomass regression + soil prediction
- forestfm library not guaranteed on PyPI — falls back to raw demo mode
- Very small model (10.9M) — low resource requirements
- 3 forest classes: low, medium, high
- Sentinel file: /data/.naturecode-earth-ready-v1

## Update Reminder
- Monitor naturecodeproject/earth for larger model variants
- Watch for forestfm PyPI package
- Consider adding temporal change detection
- Could add deforestation alert endpoint
