# naturecode-earth — Test Report

Cluster 230, gateway ClusterIP `http://10.43.79.101:80`. Type: science/predict (Naturecode Earth / ForestFM, GPU). id `naturecode-earth`.

## Status: DEMO verified 2026-06-06 (weights GATED)
`naturecodeproject/earth` returns 403 on HF (gated repo; token lacks access). Service
must run in demo mode until HF access is granted.

## Verified this pass

### POST /v1/science/predict — demo — PASS
```bash
GW=http://10.43.79.101
curl -s -X POST $GW/v1/science/predict -H 'Content-Type: application/json' \
  -d '{"model":"naturecode-earth","demo":true}'
```
→ `segmentation_probs` (synthetic land-cover probabilities). PASS via gateway (~2 min cold-start).

## Key fixes
- Init: gated download is best-effort (does not fail setup on 403).
- Runtime: install fastapi/uvicorn/numpy separately from forestfm (atomic pip was failing).
- Load: missing weights → `model = {"_demo": True}` (was crashing on `torch.load` FileNotFoundError).

## Blockers for production
- Request HF access for `naturecodeproject/earth` on the cluster token.
- `forestfm` not on PyPI; may need source install from repo.

## Card parity
id=naturecode-earth, type=embed, gpu=true, status=demo (gated weights).
Endpoint: `/v1/science/predict`.
