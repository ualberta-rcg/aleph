# Timer — Universal Time-Series Forecasting (Base)

## Source
- HuggingFace: https://huggingface.co/thuml/timer-base-84m
- License: Apache 2.0

## Deployment Summary
- **Model**: Timer-base-84M
- **GPU**: 1x L40S (shared)
- **PVC**: timer-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/forecast` — time-series forecasting
- Input: time_series, prediction_length
- Output: forecast array

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC (all-in-one)
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- transformers (AutoModelForCausalLM with trust_remote_code)
- torch (CUDA)

## Gateway Integration
- ISVC name: `timer`
- MODEL_TYPE: forecast
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: not listed (should be added)

## Audit Notes
- Uses trust_remote_code=True for custom model code
- Base variant (84M) — also see timer-xl-1b (1B) for stronger results
- No separate PVC file

## Update Reminder
- Check for Timer v2 releases
- Consider upgrading to timer-xl-1b for better accuracy
