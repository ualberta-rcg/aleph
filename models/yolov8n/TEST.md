# yolov8n — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: object detection (ONNX, CPU). id `yolov8n`.

## Scale-up
- Cold start: venv (onnxruntime, ultralytics, pillow) + export `yolov8n.pt` → ONNX.
  `3/3 Running`. ~5-6 min on first cold start (model download + ONNX export).
  Warm restart < 30s (venv + ONNX cached on PVC).

## Endpoint tests (PASS)

### POST /v1/vision/detect
```bash
IMG="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
curl -s -X POST $GW/v1/vision/detect -H 'Content-Type: application/json' \
  -d "{\"model\":\"yolov8n\",\"image\":\"$IMG\"}"
```
→ `{"model":"yolov8n","task":"detect","detections":[]}`. PASS (1×1 white image → no detections).

### Catalog
- `GET /v1/models?all=true` → `yolov8n` discovered, type=detect. PASS.

## Not applicable
- OpenAI chat / Anthropic / reasoning: N/A.

## Card parity
id=yolov8n, k8s_name=yolov8n, type=detect, gpu=false, endpoint /v1/vision/detect,
COCO 80-class detection.
