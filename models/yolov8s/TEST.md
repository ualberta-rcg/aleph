# yolov8s — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: object detection (ONNX, CPU). id `yolov8s`.

## Scale-up
- Cold start: venv + export `yolov8s.pt` → ONNX. `3/3 Running`. ~5-6 min first cold start.

## Endpoint tests (PASS)

### POST /v1/vision/detect
```bash
IMG="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
curl -s -X POST $GW/v1/vision/detect -H 'Content-Type: application/json' \
  -d "{\"model\":\"yolov8s\",\"image\":\"$IMG\"}"
```
→ `{"model":"yolov8s","task":"detect","detections":[]}`. PASS.

### Catalog
- `GET /v1/models?all=true` → `yolov8s` discovered, type=detect. PASS.

## Card parity
id=yolov8s, k8s_name=yolov8s, type=detect, gpu=false, endpoint /v1/vision/detect.
