# time-moe — TimeMoE-50M Time-Series Forecasting (Tsinghua)

`time-moe` serves **TimeMoE-50M** (Maple728/TimeMoE-50M) — a universal time-series forecasting model
using a mixture-of-experts decoder-only transformer. Zero-shot; supports prediction lengths
{1, 96, 192, 336, 720}.

- **Source:** https://huggingface.co/Maple728/TimeMoE-50M
- **License:** Apache-2.0
- **Framework:** transformers (AutoModelForCausalLM, trust_remote_code) + torch; bf16 on GPU

## API

`POST /v1/forecast`

```json
{ "model": "time-moe", "time_series": [/* ≥100 numeric values */], "prediction_length": 96 }
```

Returns `forecast` (length = `prediction_length`). **NB:** `prediction_length` must be one of
{1, 96, 192, 336, 720} — other values return an empty forecast.

## Deployment

- Custom FastAPI server (`server.py` embedded in the `time-moe-server` ConfigMap), persisted venv on
  PVC (caduceus pattern). `progress-deadline: 1800s`.
- 1× L40S HAMi slice (`gpumem 10240`); nodeSelector `gpu=on`. Scale-to-zero.

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=time-moe \
  python3 models/time-moe/test.py
```
