# timer-s1 — Timer-S1 Quantile Time-Series Forecasting (THUML/Tsinghua)

`timer-s1` serves **Timer-S1** (THUML/Tsinghua, 2026) — zero-shot quantile time-series forecasting
(9 quantile levels). Successor to Timer-XL-1B. bf16 on GPU.

- **Source:** THUML · **License:** Apache-2.0
- **Framework:** transformers (AutoModelForCausalLM, trust_remote_code) + torch; bf16 GPU

## API
`POST /v1/forecast` — `{ "model": "timer-s1", "time_series": [...], "prediction_length": 96 }`
→ `{ "forecast": {"mean": [...], "quantiles": {...}}, "model": "timer-s1" }`.

## Deployment
Custom FastAPI server (ConfigMap-embedded), persisted venv on PVC (caduceus pattern).
`progress-deadline: 1800s`. 1× L40S HAMi slice; nodeSelector `gpu=on`. Scale-to-zero.

## Test
```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=timer-s1 \
  python3 models/timer-s1/test.py
```
