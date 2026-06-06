# dust3r — Test Report

Cluster 230, gateway ClusterIP `http://10.43.79.101:80`. Type: science/reconstruct (DUSt3R, GPU). id `dust3r`.

## Status: FIXED + verified 2026-06-06
Inference worked but gateway reset: dense per-pixel point cloud serialized to ~31 MB JSON.
Downsampled to ≤2000 pts/image with bbox + alignment loss; opt-in `full_cloud`.

## Verified this pass

### POST /v1/science/reconstruct — PASS
```bash
GW=http://10.43.79.101
# needs >=2 base64-encoded PNG/JPEG images
curl -s -X POST $GW/v1/science/reconstruct -H 'Content-Type: application/json' \
  -d '{"model":"dust3r","images":["<b64_img1>","<b64_img2>"]}'
```
→ `num_images`, `alignment_loss`, `pointclouds[]` with `num_points`, `bbox`, downsampled
`pts3d`/`confidence`. ~330 KB via gateway. PASS.

### Opt-in full cloud
Pass `"full_cloud": true` for dense cloud (tens of MB; may exceed gateway limit).
`"max_points": 5000` to tune downsample cap (default 2000).

## Key fixes
- Downsample via `np.linspace` when points > `max_points`.
- Always return `num_points`, `bbox`, `mean_confidence`, `alignment_loss`.

## Card parity
id=dust3r, type=3d, gpu=true, status=production. Endpoint: `/v1/science/reconstruct`.
