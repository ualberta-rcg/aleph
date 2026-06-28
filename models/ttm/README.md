# ttm — IBM TinyTimeMixer Time-Series Forecasting

`ttm` serves **IBM TinyTimeMixer (TTM)** — a lightweight MLP-mixer foundation model (1-5M params) for
efficient zero-shot time-series forecasting. 512-context / 96-prediction.

- **Source:** ibm-granite/granite-tinytime-pytorch · **License:** Apache-2.0
- **Framework:** tsfm-public (TinyTimeMixer) + torch

## API
`POST /v1/science/forecast` — `{ "model": "ttm", "context": [/* univariate values */], "prediction_length": 96 }`
→ `{ "forecast": [...], "model": "ttm" }`.

## Deployment
Custom FastAPI server (ConfigMap-embedded), persisted venv on PVC (caduceus pattern).
`progress-deadline: 1800s`. 1× L40S HAMi slice; nodeSelector `gpu=on`. Scale-to-zero.

## Test
```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=ttm \
  python3 models/ttm/test.py
```
