# mast3r — Test Report

Cluster 230, gateway ClusterIP `http://10.43.79.101:80`. Type: science/match (MASt3R, GPU). id `mast3r`.

## Status: FIXED + verified 2026-06-06
`/v1/science/reconstruct` with 2 images returns a redirect message; real matching is on
`/v1/science/match`. Match handler called `.cpu()` on numpy arrays from `fast_reciprocal_NNs`.

## Verified this pass

### POST /v1/science/match — PASS
```bash
GW=http://10.43.79.101
curl -s -X POST $GW/v1/science/match -H 'Content-Type: application/json' \
  -d '{"model":"mast3r","images":["<b64_img1>","<b64_img2>"]}'
```
→ `num_matches: 473`, `returned_matches`, `matches_image1`/`matches_image2` coordinate
pairs. ~9 KB. PASS.

### POST /v1/science/reconstruct — informational
With exactly 2 images, returns message directing to `/v1/science/match`. Use match for
2-image workflows; reconstruct needs more images / pairs.

## Key fixes
- `np.asarray(matches_im1)` instead of `.cpu().numpy()`.
- Cap returned matches to `max_matches` (default 2000) for gateway body safety.

## Card parity
id=mast3r, type=3d, gpu=true, status=production. Primary card path is reconstruct but
**2-image matching uses `/v1/science/match`**.
