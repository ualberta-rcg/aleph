# granite-geospatial-ocean — Test Report

Cluster 230, gateway ClusterIP `http://10.43.79.101:80`. Type: science/embed (IBM Granite Geospatial Ocean, GPU). id `granite-geospatial-ocean`.

## Status: FIXED + verified 2026-06-06
Same terratorch/stringzilla gcc issue as biomass sibling. Init needed gcc/g++/git.
Slow cold-start (~5+ min).

## Verified this pass

### POST /v1/science/embed — demo — PASS
```bash
GW=http://10.43.79.101
curl -s -X POST $GW/v1/science/embed -H 'Content-Type: application/json' \
  -d '{"model":"granite-geospatial-ocean","demo":true}'
```
→ `embeddings` (synthetic zero vector). PASS.

### Real inference
Pass `"image"`: (C=16, H=42, W=42) Sentinel-3 bands (not yet exercised end-to-end).

## Key fixes
- Init: `apt-get install gcc g++ git` before terratorch pip.
- Sentinel: `.granite-ocean-ready-v2`.

## Card parity
id=granite-geospatial-ocean, type=classify, gpu=true, status=production.
Endpoint: `/v1/science/embed`.
