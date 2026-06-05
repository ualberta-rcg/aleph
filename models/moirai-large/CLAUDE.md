# Moirai-Large — Salesforce Universal Time-Series Forecasting (311M)

## Source
- HuggingFace: https://huggingface.co/Salesforce/moirai-1.1-R-large
- License: Apache 2.0

## Deployment Summary
- **Model**: Moirai 1.1-R-Large (311M params)
- **GPU**: 1x L40S (shared)
- **PVC**: moirai-large-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/science/forecast` — probabilistic time-series forecasting
- Input: context array, prediction_length, freq, patch_size, num_samples
- Output: mean, quantiles (0.1, 0.5, 0.9)

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + PVC + ISVC (all-in-one)
- `pvc.yaml` — moirai-large-data PVC
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- uni2ts (Salesforce time-series library)
- torch (CUDA)
- pandas

## Gateway Integration
- ISVC name: `moirai-large`
- MODEL_TYPE: forecast
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: yes
- Listed in MODEL_METADATA

## Audit Notes
- Uses /v1/science/forecast (different from base moirai's /v1/forecast)
- Context length up to 4096 (larger than base variant's 200)
- Auto patch size selection for optimal performance

## Update Reminder
- Check for newer Moirai 1.1 releases
- Standardize endpoint path across Moirai variants
