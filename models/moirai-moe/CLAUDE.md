# Moirai-MoE — Salesforce Mixture-of-Experts Time-Series Forecasting

## Source
- HuggingFace: https://huggingface.co/Salesforce/moirai-moe-1.0-R-base
- License: CC BY-NC-4.0 (non-commercial)

## Deployment Summary
- **Model**: Moirai-MoE 1.0-R-base (~150M params)
- **GPU**: 1x L40S (shared)
- **PVC**: moirai-moe-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/forecast` — time-series forecasting
- Input: time_series, prediction_length, freq
- Output: forecast with mean and quantiles

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC (all-in-one)
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- uni2ts (includes MoiraiMoEModule, MoiraiMoEForecast)
- torch (CUDA)

## Gateway Integration
- ISVC name: `moirai-moe`
- MODEL_TYPE: forecast
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: not listed (should be added)

## Audit Notes
- CC BY-NC-4.0 license (non-commercial) — differs from base/large Apache 2.0
- Uses /v1/forecast (same as base moirai, different from moirai-large)
- No separate PVC file — PVC embedded in inferenceservice.yaml

## Update Reminder
- Check for newer Moirai-MoE releases
- Note non-commercial license restriction
