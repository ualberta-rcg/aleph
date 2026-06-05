# MOMENT — Open Time-Series Foundation Model (CMU)

## Source
- HuggingFace: https://huggingface.co/AutonLab/MOMENT-1-large
- License: Apache 2.0

## Deployment Summary
- **Model**: MOMENT-1-large (385M params)
- **GPU**: 1x L40S (shared)
- **PVC**: moment-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/forecast` — time-series forecasting
- `POST /v1/embed` — time-series embeddings
- Input: time_series array, prediction_length
- Output: forecast values

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC (all-in-one)
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- momentfm (MOMENTPipeline)
- torch (CUDA)

## Gateway Integration
- ISVC name: `moment`
- MODEL_TYPE: forecast
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: not listed (should be added)

## Audit Notes
- Multi-task model: supports forecasting, classification, anomaly detection, imputation
- T5-based architecture (unusual for time series)
- No separate PVC file

## Update Reminder
- Check for newer MOMENT releases
- Explore enabling classification and anomaly detection endpoints
