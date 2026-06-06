# earthpt — Test Report

Cluster 230, gateway ClusterIP `http://10.43.79.101:80`. Type: science/predict (EarthPT-700M, GPU vGPU). id `earthpt`.

## Status: FIXED + verified 2026-06-06
Was crash-looping on startup: checkpoint loaded straight to GPU in fp32 (OOM past 10 GiB
vGPU cap), then host-RAM OOMKilled (8 Gi limit) during CPU load. Fixed CPU load → half →
move; bumped container RAM to 24 Gi.

## Verified this pass

### POST /v1/science/predict — PASS
```bash
GW=http://10.43.79.101
curl -s -X POST $GW/v1/science/predict -H 'Content-Type: application/json' \
  -d '{"model":"earthpt","predict_steps":3,"time_series":[[0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8],[0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9]]}'
```
→ `predictions` array (3 steps × 14 spectral channels). PASS.

## Key fixes
- `torch.load(..., map_location="cpu")` then `.half().to(DEVICE)` (not fp32 direct-to-GPU).
- Container memory: requests 8Gi / limits 24Gi (was 4Gi/8Gi).

## Card parity
id=earthpt, type=embed, gpu=true, status=production. Endpoint: `/v1/science/predict`.
Input: `time_series` (list of 18-float rows: 14 MODIS bands + 4 time features).
