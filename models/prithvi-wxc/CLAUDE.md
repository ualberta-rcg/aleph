# Prithvi-WxC 2.3B — NASA-IBM Weather-Climate Foundation Model

## Source
- HuggingFace: https://huggingface.co/ibm-nasa-geospatial/Prithvi-WxC-1.0-2300M-rollout
- GitHub: https://github.com/nasa-impact/prithvi-wxc
- License: Apache 2.0

## Deployment Summary
- **Model**: Prithvi-WxC 2.3B (28.4GB checkpoint)
- **GPU**: 1x L40S (dedicated)
- **PVC**: prithvi-wxc-data (inline in ISVC)
- **Scale-to-zero**: Yes (minReplicas: 0, 30min retention)
- **Venv**: No (pip install on every start)

## API
- `POST /v1/science/forecast` — MERRA-2 state to weather forecast
- Input: state dict + lead_time (multiples of 6h, up to 168h)
- Output: forecast state dict
- Demo mode: returns synthetic forecast

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + init container
- `details.yaml` — model metadata ConfigMap
- No separate pvc.yaml

## Dependencies
- PrithviWxC (from GitHub repo)
- torch (CUDA 12.6), pyyaml, einops, timm, netCDF4
- fastapi, uvicorn

## Audit Notes
- 28.4GB checkpoint — download takes 30-60 min on first setup
- Atomic lock directory pattern for safe concurrent setup
- Uses FP16 on GPU for memory efficiency
- 160 input channels + 8 static channels + output scalers
- Demo mode only — full inference pipeline not yet implemented
- Very high memory: 64Gi request / 96Gi limit
- Sentinel file: /data/.prithvi-wxc-ready-v1

## Update Reminder
- Implement full MERRA-2 inference pipeline
- Consider 4-GPU deployment for faster inference
- Monitor nasa-impact/prithvi-wxc for API updates
- Could add ensemble forecasting with stochastic variant
