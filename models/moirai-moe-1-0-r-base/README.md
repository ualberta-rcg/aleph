# moirai-moe-1-0-r-base — Moirai-MoE Time-Series Forecasting (Salesforce)

`moirai-moe-1-0-r-base` serves **Salesforce Moirai-MoE** (moirai-moe-1.0-R-base, ~935M
mixture-of-experts) — a universal zero-shot time-series forecasting model. Any-variate, configurable
prediction/context length. Returns mean + quantile forecasts.

- **Source:** https://huggingface.co/Salesforce/moirai-moe-1.0-R-base
- **License:** CC-BY-NC-4.0 (non-commercial)
- **Framework:** `uni2ts` (`MoiraiMoEModule`) + torch + GluonTS

## API

`POST /v1/forecast`

```json
{ "model": "moirai-moe-1-0-r-base", "time_series": [/* numeric series */], "prediction_length": 24 }
```

Returns `forecast` (`{mean, quantiles}`). The server reads `time_series` + `prediction_length`
(`model` is the gateway routing id).

## Deployment

- Custom FastAPI server (`server.py` embedded in the `moirai-moe-1-0-r-base-server` ConfigMap, mounted
  read-only at `/app`), run via a persisted venv on the PVC (caduceus pattern).
- initContainer builds `/data/venv` (`uni2ts` + torch) and caches the model — gated → fast cold starts.
  `progress-deadline: 1800s` (uni2ts slow init).
- 1× L40S HAMi slice; nodeSelector `gpu=on`. Scale-to-zero (`minReplicas: 0`, 15m idle).

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=moirai-moe-1-0-r-base \
  python3 models/moirai-moe-1-0-r-base/test.py
```
Forecasts a 96-point series over horizon 24, asserts mean + finite values.
