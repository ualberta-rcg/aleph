# depth-anything

Depth Anything V2 Small monocular depth model served as a KServe custom predictor.

- Model id: `depth-anything-v2`
- Endpoint: `POST /v1/vision/depth`
- Runtime: ONNX Runtime (`onnx-community/depth-anything-v2-small`)

## HF / upstream I/O reference

- ONNX repo: <https://huggingface.co/onnx-community/depth-anything-v2-small>
- Base model: `depth-anything/Depth-Anything-V2-Small`
- Task: depth estimation from a single RGB image.
- Input: one RGB image.
- Output: depth map; this server returns a base64 PNG depth image, a compact 64x64 grid, and depth stats.

## Gateway request

```json
{
  "model": "depth-anything-v2",
  "image": "<base64-png-or-jpg>"
}
```

## Gateway response

```json
{
  "model": "depth-anything-v2",
  "task": "depth",
  "width": 1280,
  "height": 720,
  "depth_png_base64": "<...>",
  "depth_grid_64": [[0.1,0.2]],
  "stats": {"raw_min":0.01,"raw_max":7.12,"raw_mean":1.83}
}
```
