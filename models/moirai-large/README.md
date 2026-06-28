# moirai-large — Universal Time-Series Forecasting (Salesforce Moirai 1.1-R-Large)

`moirai-large` serves **Salesforce Moirai 1.1-R-Large** (311M) — the larger variant of the Moirai
universal zero-shot time-series forecasting foundation model. Any-variate, configurable
prediction/context length (up to 4096) + automatic patch size. Returns mean + quantile forecasts.

- **Source:** https://huggingface.co/Salesforce/moirai-1.1-R-large
- **License:** Apache-2.0
- **Framework:** `uni2ts` + torch + GluonTS

## API

`POST /v1/science/forecast`

```json
{ "model": "moirai-large", "context": [/* numeric series */], "prediction_length": 24, "num_samples": 100 }
```

Returns `mean` (length = `prediction_length`) and `quantiles` (`{0.1, 0.5, 0.9}`). The server reads
`context` (the series) + `prediction_length`/`freq`/`num_samples` (`model` is the gateway routing id).

## Deployment

- Custom FastAPI server (`server.py` embedded in the `moirai-large-server` ConfigMap, mounted
  read-only at `/app`), run via a persisted venv on the PVC (caduceus pattern).
- initContainer builds `/data/venv` (`uni2ts` + torch) and loads the model — gated → fast cold starts.
  **`progress-deadline: 1800s`** (the uni2ts venv install is slow — see the moirai lesson).
- 1× L40S HAMi slice; nodeSelector `gpu=on`. Scale-to-zero (`minReplicas: 0`, 15m idle).

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=moirai-large \
  python3 models/moirai-large/test.py
```
Forecasts a 96-point series over horizon 24, asserts mean + quantiles.
