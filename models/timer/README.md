# timer — Universal Zero-Shot Time-Series Forecasting (Timer, THUML/Tsinghua)

`timer` serves **Timer-base-84M** (thuml/timer-base-84m) — a universal zero-shot time-series
forecasting model (decoder-only transformer, 84M). Configurable prediction lengths.

- **Source:** https://huggingface.co/thuml/timer-base-84m · **License:** Apache-2.0
- **Framework:** transformers (AutoModelForCausalLM, trust_remote_code) + torch; fp16 GPU

## API
`POST /v1/forecast` — `{ "model": "timer", "time_series": [...], "prediction_length": 96 }`
→ `{ "forecast": [...], "model": "timer" }`.

## Deployment
Custom FastAPI server (ConfigMap-embedded), persisted venv on PVC (caduceus pattern).
`progress-deadline: 1800s`. 1× L40S HAMi slice; nodeSelector `gpu=on`. Scale-to-zero.

## Test
```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=timer \
  python3 models/timer/test.py
```
