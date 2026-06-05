# Granite Geospatial Biomass — Above-Ground Biomass Estimation

## Source
- HuggingFace: https://huggingface.co/ibm-granite/granite-geospatial-biomass
- License: Apache 2.0

## Deployment Summary
- **Model**: Granite Geospatial Biomass (Swin-B + UPerNet, ~350MB)
- **GPU**: 1x L40S (dedicated)
- **PVC**: granite-geospatial-biomass-data (inline in ISVC)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: No (pip install on every start)

## API
- `POST /v1/science/predict` — HLS imagery to biomass map
- Input: (C=6, H, W) HLS reflectance array
- Output: (H, W) biomass Mg/ha per pixel + scene mean
- Demo mode: returns sinusoidal synthetic biomass map

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + init container
- `details.yaml` — model metadata ConfigMap
- No separate pvc.yaml

## Dependencies
- terratorch (LightningInferenceModel)
- torch + torchvision (CUDA 12.6)
- fastapi, uvicorn, huggingface_hub

## Audit Notes
- Loads via LightningInferenceModel.from_config()
- Sentinel file: /data/.granite-biomass-ready-v1
- 6 HLS bands: Blue, Green, Red, NIR, SWIR1, SWIR2
- Fine-tuned on GEDI L4A across 15 biomes
- Prithvi-EO backbone with UPerNet decoder

## Update Reminder
- Monitor ibm-granite for model updates
- Consider adding uncertainty estimation
- Could add temporal change detection endpoint
