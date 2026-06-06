# granite-geospatial-biomass — Test Report

Cluster 230, gateway ClusterIP `http://10.43.79.101:80`. Type: science/predict (IBM Granite Geospatial Biomass, GPU). id `granite-geospatial-biomass`.

## Status: FIXED + verified 2026-06-06
Init container crashed building `terratorch` → `stringzilla` (no gcc in python:3.11-slim).
Added gcc/g++/git; bumped sentinel to v2. Slow cold-start (~5+ min: terratorch pip in runtime).

## Verified this pass

### POST /v1/science/predict — demo — PASS
```bash
GW=http://10.43.79.101
curl -s -X POST $GW/v1/science/predict -H 'Content-Type: application/json' \
  -d '{"model":"granite-geospatial-biomass","demo":true}'
```
→ `biomass_map` (synthetic 50 Mg/ha grid). PASS.

### Real inference
Pass `"image"`: (C=6, H, W) HLS reflectance array (not yet exercised end-to-end).

## Key fixes
- Init: `apt-get install gcc g++ git` before terratorch pip.
- Sentinel: `.granite-biomass-ready-v2` (forces rebuild with compiler).

## Card parity
id=granite-geospatial-biomass, type=classify, gpu=true, status=production.
Endpoint: `/v1/science/predict`.
