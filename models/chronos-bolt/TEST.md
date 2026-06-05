# chronos-bolt — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: forecast (CPU). id `chronos-bolt`.

## Scale-up
- Cold start: HF download (amazon/chronos-bolt-base) + venv (chronos-forecasting), then
  pipeline load. `3/3 Running`. Cold-start guard returns friendly 503 until ready. ~5 min.

## Endpoint test (PASS)
### POST /v1/forecast
```bash
curl -s -X POST $GW/v1/forecast -H "Content-Type: application/json" \
  -d '{"model":"chronos-bolt","values":[1,2,...,20],"horizon":6}'
```
→ `horizon=6`, `mean_len=6` (mean/median/quantiles returned). PASS.

### Catalog
- `GET /v1/models?all=true` → `chronos-bolt` discovered (type=forecast). PASS.

## Not applicable
- OpenAI chat / Anthropic / reasoning: N/A (time-series forecaster).

## Card parity
id=chronos-bolt, k8s_name=chronos-bolt, type=forecast, primary `/v1/forecast`,
defaults horizon=12 / quantiles [0.1,0.5,0.9], gpu=false.
