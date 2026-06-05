# efficientnet-b0 — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: image classification (CPU). id `efficientnet-b0`.

## Scale-up
- Cold start: venv + ONNX model download. `3/3 Running`. ~3-4 min cold.

## Endpoint tests (PASS)

### POST /v1/vision/classify
```bash
IMG="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
curl -s -X POST $GW/v1/vision/classify -H 'Content-Type: application/json' \
  -d "{\"model\":\"efficientnet-b0\",\"image\":\"$IMG\"}"
```
→ `{"model":"efficientnet-b0","task":"classify","predictions":[{"rank":1,"class_id":892,...},...]}`. PASS.

### Catalog
- `GET /v1/models?all=true` → `efficientnet-b0` discovered, type=classify. PASS.

## Card parity
id=efficientnet-b0, k8s_name=efficientnet-b0, type=classify, gpu=false,
endpoint /v1/vision/classify.
