# megadetector

MegaDetector v5 wildlife camera-trap detector (animals/humans/vehicles), served as a KServe custom predictor.

- Model id: `megadetector`
- Endpoint: `POST /v1/vision/detect` (legacy aliases: `/v1/detect`, `/v1/science/detect`)
- Runtime: `megadetector` Python package + PyTorch checkpoint (`md_v5a.0.0.pt`)

## HF / upstream I/O reference

- Upstream project: <https://github.com/microsoft/CameraTraps>
- Task: camera-trap object detection with three categories: `animal`, `human`, `vehicle`.
- Input: image(s) and detection threshold.
- Output: normalized bounding boxes and confidence per detection.

## Gateway request

```json
{
  "model": "megadetector",
  "image": "<base64-png-or-jpg>",
  "threshold": 0.2
}
```

Batch mode is also supported with `images: ["<b64>", "..."]`.

## Gateway response

```json
{
  "model": "megadetector",
  "threshold": 0.2,
  "detections": [[{"category":"animal","bbox":[x,y,w,h],"conf":0.91}]]
}
```
