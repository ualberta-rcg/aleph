# fengwu — Test Report

Cluster 230, gateway ClusterIP `http://10.43.79.101:80`. Type: science/forecast (FengWu v2 ONNX, GPU). id `fengwu`.

## Status: FIXED + verified 2026-06-06
Pod returned 200 but gateway reset connection: demo response was 286 MB raw grid JSON
(4×721×1440 surface + 5×13×721×1440 upper). Summarized to shape/stats/downsampled preview.

## Verified this pass

### POST /v1/science/forecast — demo — PASS
```bash
GW=http://10.43.79.101
curl -s -X POST $GW/v1/science/forecast -H 'Content-Type: application/json' \
  -d '{"model":"fengwu","demo":true}'
```
→ `surface`/`upper` summaries with shape, min/max/mean/std, 8×8 preview. PASS via gateway.

### Opt-in full grid
Pass `"full_grid": true` for raw arrays (hundreds of MB; may exceed gateway body limit).

## Key fixes
- Added `_summarize()` helper; default response is compact summary.
- Real ONNX inference path also summarized unless `full_grid=true`.

## Card parity
id=fengwu, type=forecast, gpu=true, status=production. Endpoint: `/v1/science/forecast`.
Real inference needs `surface` (4,721,1440) + `upper` (5,13,721,1440) arrays.
