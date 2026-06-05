# Timer-XL-1B — Large Universal Time-Series Forecasting

## Source
- HuggingFace: https://huggingface.co/thuml/Timer-XL-1B
- License: Apache 2.0

## Deployment Summary
- **Model**: Timer-XL-1B (1B params)
- **GPU**: 1x L40S (shared)
- **PVC**: timer-xl-1b-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/forecast` — time-series forecasting
- Input: time_series (min 96 values), prediction_length
- Output: forecast array, input_length, prediction_length

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC (all-in-one)
- `pvc.yaml` — timer-xl-1b-data PVC
- `README.md` — model documentation
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- transformers (AutoModelForCausalLM with trust_remote_code)
- torch (CUDA)

## Gateway Integration
- ISVC name: `timer-xl-1b`
- MODEL_TYPE: forecast
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: not listed (should be added)

## Audit Notes
- Larger variant of timer-base-84m (12x more parameters)
- Uses trust_remote_code=True
- Minimum 96 input values recommended
- 15K downloads on HuggingFace

## Update Reminder
- Check for Timer-XL v2 releases
- Monitor thuml/Timer-XL-1B for updates
