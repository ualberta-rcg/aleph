# chronos-bolt — Zero-Shot Time-Series Forecasting (Chronos-Bolt)

`chronos-bolt` serves **Chronos-Bolt** (amazon/chronos-bolt-base) — a zero-shot probabilistic
time-series forecasting model. Given a numeric series, it returns median/mean + quantile forecasts.
**CPU-only.**

- **Source:** https://huggingface.co/amazon/chronos-bolt-base
- **License:** Apache-2.0
- **Framework:** `chronos-forecasting` (`BaseChronosPipeline`) + torch (CPU)

## API

`POST /v1/forecast`

```json
{ "model": "chronos-bolt", "values": [10, 12, 15, 14, 17, 20], "horizon": 12, "num_samples": 20 }
```

Returns `median`, `mean`, and `quantiles` (default `{0.1, 0.5, 0.9}`), each length `horizon`. The
server reads `values` (the series) + `horizon` (`model` is the gateway routing id).

## Deployment

- Custom FastAPI server (`server.py` embedded in the `chronos-bolt-server` ConfigMap, mounted
  read-only at `/app`), run via a persisted venv on the PVC (caduceus pattern).
- initContainer builds `/data/venv` (`chronos-forecasting` + fastapi/uvicorn) and downloads
  `amazon/chronos-bolt-base` — both gated → fast cold starts.
- **CPU-only** (no GPU request); runs on workers. Scale-to-zero (`minReplicas: 0`, 15m idle).

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=chronos-bolt \
  python3 models/chronos-bolt/test.py
```
Forecasts a 16-point series over horizon 12, asserts median length + finite values.
