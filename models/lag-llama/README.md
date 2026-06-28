# lag-llama — Probabilistic Zero-Shot Time-Series Forecasting (Lag-Llama)

`lag-llama` serves **Lag-Llama** (time-series-foundation-models/Lag-Llama, ~200M) — a probabilistic
foundation model for zero-shot time-series forecasting. Lag-based tokenization + a decoder-only
transformer. Returns mean + quantile forecasts via GluonTS sampling.

- **Source:** https://huggingface.co/time-series-foundation-models/Lag-Llama
- **License:** Apache-2.0
- **Framework:** torch + GluonTS (lag-based decoder transformer)

## API

`POST /v1/science/forecast`

```json
{ "model": "lag-llama", "context": [/* numeric series */], "prediction_length": 24, "num_samples": 100 }
```

Returns `mean` (length = `prediction_length`), `quantiles` (`{0.1, 0.9}`), and raw `samples`. The
server reads `context` + `prediction_length`/`num_samples` (`model` is the gateway routing id).

## Deployment

- Custom FastAPI server (`server.py` embedded in the `lag-llama-server` ConfigMap, mounted read-only at
  `/app`), run via a persisted venv on the PVC (caduceus pattern). Dropped the vestigial
  `kustomization.yaml`.
- initContainer builds `/data/venv` (torch + GluonTS) and loads the model — gated → fast cold starts.
  `progress-deadline: 1800s`.
- 1× L40S HAMi slice; nodeSelector `gpu=on`. Scale-to-zero (`minReplicas: 0`, 15m idle).

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=lag-llama \
  python3 models/lag-llama/test.py
```
Forecasts a 96-point series over horizon 24, asserts mean + finite values.
