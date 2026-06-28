# moirai — Universal Time-Series Forecasting (Salesforce Moirai)

`moirai` serves **Salesforce Moirai** (moirai-1.0-R-base, ~91M) — a universal zero-shot time-series
forecasting foundation model (any-variate, configurable prediction/context length + patch size).
Returns mean + quantile forecasts.

- **Source:** https://huggingface.co/Salesforce/moirai-1.0-R-base
- **License:** Apache-2.0
- **Framework:** `uni2ts` (`MoiraiForecast`) + torch + GluonTS

## API

`POST /v1/forecast`

```json
{ "model": "moirai", "values": [/* numeric series */], "horizon": 12 }
```

Returns `forecast` (`{mean, quantile_10, quantile_90}`, each length = `horizon`). The server reads
`values` + `horizon` (`model` is the gateway routing id).

## Deployment

- Custom FastAPI server (`server.py` embedded in the `moirai-server` ConfigMap, mounted read-only at
  `/app`), run via a persisted venv on the PVC (caduceus pattern).
- initContainer builds `/data/venv` (`uni2ts` + torch) and loads the model — gated → fast cold starts.
- 1× L40S HAMi slice; nodeSelector `gpu=on`. Scale-to-zero (`minReplicas: 0`, 15m idle).

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=moirai \
  python3 models/moirai/test.py
```
Forecasts a 96-point series over horizon 12, asserts mean length + finite values.
