# Moirai (Base) — Salesforce Universal Time-Series Forecasting

## Source
- HuggingFace: https://huggingface.co/Salesforce/moirai-1.0-R-base
- License: Apache 2.0

## Deployment Summary
- **Model**: Moirai 1.0-R-base (~91M params)
- **GPU**: 1x L40S (shared), falls back to CPU
- **PVC**: moirai-data (5Gi NFS)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/forecast` — time-series forecasting
- Input: values array, horizon (prediction steps)
- Output: mean, quantile_10, quantile_90

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + PVC + ISVC (all-in-one)
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- uni2ts (Salesforce time-series library)
- torch >= 2.6 (CUDA 12.6)
- gluonts, pandas

## Gateway Integration
- ISVC name: `moirai`
- MODEL_TYPE: forecast
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: not listed (should be added)

## Audit Notes
- Base variant of the Moirai family (vs moirai-large 311M, moirai-moe)
- Uses /v1/forecast endpoint (not /v1/science/forecast like moirai-large)
- NFS PVC (ReadWriteOnce with nfs-models storage class)

## Update Reminder
- Check for newer Moirai versions
- Consider standardizing endpoint path across Moirai variants
