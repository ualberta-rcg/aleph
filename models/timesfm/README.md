# timesfm — Time-Series Foundation Model (Google TimesFM, 500M)

`timesfm` serves **Google TimesFM** (google/timesfm-2.0-500m-pytorch, ~500M) — a decoder-only
foundation model for time-series forecasting (patch-decoder trained on real-world series). Returns
point + median + quantile forecasts.

- **Source:** https://huggingface.co/google/timesfm-2.0-500m-pytorch
- **License:** Apache-2.0
- **Framework:** `timesfm` (`TimesFmModelForPrediction`) + torch

## API

`POST /v1/forecast`

```json
{ "model": "timesfm", "values": [/* numeric series */], "horizon": 24 }
```

Returns `mean`, `median`, and `quantiles`. The server reads `values`/`time_series`/`series` + `horizon`
(`model` is the gateway routing id).

## Deployment

- Custom FastAPI server (`server.py` embedded in the `timesfm-server` ConfigMap, mounted read-only at
  `/app`), run via a persisted venv on the PVC (caduceus pattern).
- initContainer builds `/data/venv` (`timesfm` + torch) and loads the model — gated → fast cold starts.
  `progress-deadline: 1800s`.
- 1× L40S HAMi slice (`gpumem 10240`); nodeSelector `gpu=on`. Scale-to-zero (`minReplicas: 0`, 15m).

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=timesfm \
  python3 models/timesfm/test.py
```
Forecasts a 96-point series over horizon 24, asserts mean + finite values.
