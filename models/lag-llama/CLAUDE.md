# Lag-Llama — Probabilistic Time-Series Foundation Model

## Source
- HuggingFace: https://huggingface.co/time-series-foundation-models/lag-llama
- License: Apache 2.0

## Deployment Summary
- **Model**: Lag-Llama (~30M params)
- **GPU**: 1x L40S (shared), falls back to CPU
- **PVC**: lag-llama-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/science/forecast` — probabilistic time-series forecasting
- Input: context array, prediction_length, num_samples, freq
- Output: mean, quantiles (0.1, 0.5, 0.9)

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + PVC + ISVC (all-in-one)
- `pvc.yaml` — lag-llama-data PVC
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- lag-llama (pip)
- torch (CUDA)
- gluonts, pandas

## Gateway Integration
- ISVC name: `lag-llama`
- MODEL_TYPE: forecast
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: yes

## Audit Notes
- Uses LagLlamaEstimator with checkpoint loading
- GluonTS PandasDataset for input formatting
- Reconfigures prediction_length per request

## Update Reminder
- Check for new Lag-Llama releases
- Monitor lag-llama package for API changes
