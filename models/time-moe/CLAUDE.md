# TimeMoE — Mixture-of-Experts Time-Series Forecasting

## Source
- HuggingFace: https://huggingface.co/Maple728/TimeMoE-50M
- Paper: arxiv 2409.16040
- License: Apache 2.0

## Deployment Summary
- **Model**: TimeMoE-50M
- **GPU**: 1x L40S (shared), falls back to CPU
- **PVC**: time-moe-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/forecast` — time-series forecasting
- Input: time_series, prediction_length (1/96/192/336/720)
- Output: forecast array

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + PVC + ISVC (all-in-one)
- `pvc.yaml` — time-moe-data PVC
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- transformers (trust_remote_code=True)
- torch (CUDA)

## Gateway Integration
- ISVC name: `time-moe`
- MODEL_TYPE: forecast
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: not listed (should be added)

## Audit Notes
- Uses trust_remote_code=True for custom model code
- Supports specific prediction lengths only: 1, 96, 192, 336, 720
- 336K downloads on HuggingFace

## Update Reminder
- Check for larger TimeMoE variants
- Monitor for prediction length flexibility improvements
