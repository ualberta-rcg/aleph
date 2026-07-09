# sam3.1 — SAM 3 promptable image segmentation

**Source:** [`facebook/sam3`](https://huggingface.co/facebook/sam3) (gated, access approved)
**Type:** open-vocabulary image segmentation (text → masks)
**Params:** 848M · **Precision:** fp32 · **GPU:** HAMi slice (10 GB) · **Scale-to-zero:** yes

## What it does

Give SAM 3 ("Segment Anything with Concepts", Meta AI) a short text phrase naming a
concept — e.g. `"a dog"`, `"person"`, `"car"`, `"a player in red"` — and it **detects
and segments every instance** of that concept in the image, returning a per-instance
mask, bounding box, area, and confidence score. Handles 270K+ unique concepts.

## Endpoint

`POST /v1/science/segment`

```json
{
  "model": "sam3.1",
  "image": "<base64 JPEG/PNG>",
  "text": "a dog",
  "return_masks": false
}
```

Response:

```json
{
  "model": "sam3.1",
  "task": "segment",
  "prompt": "a dog",
  "count": 2,
  "image_size": [480, 640],
  "instances": [
    {"score": 0.92, "box": [120, 80, 300, 420], "area": 38421},
    {"score": 0.87, "box": [400, 100, 560, 410], "area": 31102}
  ]
}
```

Set `return_masks: true` to add a base64 PNG boolean mask per instance
(`mask_png`) — large payloads, off by default.

## Cold start

First boot is slow: the initContainer builds a torch cu128 venv + installs the `sam3`
package from GitHub, then downloads the ~3.4 GB `sam3.pt` checkpoint. Subsequent cold
starts reuse the cached venv/checkpoint on the PVC (~30–60 s). Expect **6–10 min** on
the very first wake, ~1 min after.

## Run the test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 \
  python3 models/sam3.1/test.py
```
