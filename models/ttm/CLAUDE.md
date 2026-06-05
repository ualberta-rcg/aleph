# TTM — IBM TinyTimeMixer (Granite)

## Source
- HuggingFace: https://huggingface.co/ibm-granite/granite-timeseries-ttm-r2
- License: Apache 2.0

## Deployment Summary
- **Model**: Granite TTM-R2 (1-5M params, extremely lightweight)
- **GPU**: 1x L40S (shared)
- **PVC**: ttm-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv2 on PVC, uses venv2 to avoid conflicts)

## API
- `POST /v1/science/forecast` — multi-variate time-series forecasting
- Input: context (univariate or multi-variate), prediction_length
- Output: forecast array

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + PVC + ISVC (all-in-one)
- `pvc.yaml` — ttm-data PVC
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- granite-tsfm / tsfm_public
- torch (CUDA 12.6)
- huggingface_hub

## Gateway Integration
- ISVC name: `ttm`
- MODEL_TYPE: forecast
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: yes
- Listed in MODEL_METADATA

## Audit Notes
- Very small model (1-5M params) — fast inference
- Uses venv2 path (may conflict with other models sharing PVC)
- Requires CA certificate fix in init container
- HF_TOKEN required for model download

## Update Reminder
- Check for newer TTM releases
- Monitor granite-tsfm package for API changes
