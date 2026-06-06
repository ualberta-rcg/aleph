# fourcastnet3 — Test Report

Cluster 230, gateway ClusterIP `http://10.43.79.101:80`. Type: science/forecast (NVIDIA FourCastNet v3, GPU). id `fourcastnet3`.

## Status: DEMO verified 2026-06-06 (real FCN3 blocked)
Attempted real FCN3 via earth2studio 0.15: needs NVIDIA `makani` (GitHub only) +
`torch-harmonics` compiled against a pinned torch/torchvision/CUDA stack. Runtime pip
cannot resolve the matrix (makani clobbers torchvision; torch-harmonics _C ABI mismatch;
CUDA major version conflicts). **Needs a purpose-built container image.**

## Verified this pass

### POST /v1/science/forecast — demo — PASS
```bash
GW=http://10.43.79.101
curl -s -X POST $GW/v1/science/forecast -H 'Content-Type: application/json' \
  -d '{"model":"fourcastnet3","demo":true,"steps":2}'
```
→ `forecasts[]` with step, lead_hours, synthetic `t2m` values. PASS via gateway.

### Real inference — BLOCKED
Server falls back to demo when FCN3 load fails. Real rollout code exists (iterator +
summarized t2m) but cannot load weights without dedicated image.

## Key fixes attempted
- Correct class: `FCN3` (not deprecated `FourCastNet`).
- Pin `earth2studio>=0.15,<0.16`; install makani from GitHub; reorder torch reinstall.
- Conclusion: runtime pip is not viable; bake deps into image.

## Card parity
id=fourcastnet3, type=forecast, gpu=true, status=demo (not production until image built).
Endpoint: `/v1/science/forecast`.
