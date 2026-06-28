# moment — Time-Series Foundation Model (MOMENT-1-large)

`moment` serves **MOMENT-1-large** (AutonLab/CMU, 385M) — an open time-series foundation model
(T5-based) supporting forecasting, classification, anomaly detection, and imputation. This deployment
exposes forecasting and embeddings.

- **Source:** https://huggingface.co/AutonLab/MOMENT-1-large
- **License:** Apache-2.0
- **Framework:** `momentfm` (`MOMENTPipeline`) + torch

## API

`POST /v1/forecast`

```json
{ "model": "moment", "time_series": [/* 512 numeric values */], "prediction_length": 96 }
```

Returns `forecast` (length = `prediction_length`). The server reads `time_series` +
`prediction_length` (`model` is the gateway routing id). `POST /v1/embed` for time-series embeddings.

## Deployment

- Custom FastAPI server (`server.py` embedded in the `moment-server` ConfigMap, mounted read-only at
  `/app`), run via a persisted venv on the PVC (caduceus pattern).
- initContainer builds `/data/venv` (`momentfm` + torch) and loads the model — gated → fast cold starts.
- 1× L40S HAMi slice; nodeSelector `gpu=on`. Scale-to-zero (`minReplicas: 0`, 15m idle).

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=moment \
  python3 models/moment/test.py
```
Forecasts a 512-point series over horizon 96, asserts forecast length + finite values.
