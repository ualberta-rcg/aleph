# arcface — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: face/vision (CPU, ONNX). id `arcface-resnet100`.

## Scale-up
- Cold start: venv build + hf_hub_download of `arcface.onnx`, then onnxruntime session.
  Pod `3/3 Running`, `/health` 200. Cold start ~2 min.

## Endpoint tests (PASS)

### POST /v1/vision/face
Sent a synthetic 112x112 PNG (base64) as `image`:
```bash
curl -s -X POST $GW/v1/vision/face -H "Content-Type: application/json" \
  -d '{"model":"arcface-resnet100","image":"<base64-png>"}'
```
→ `dim=512`, L2-norm ≈ 1.0 (verified `sum(x^2)≈1`). PASS.

### Catalog
- `GET /v1/models?all=true` → `arcface-resnet100` discovered (type=face). PASS.

## Not applicable
- OpenAI chat / Anthropic / reasoning: N/A (vision embedding model).

## Card parity
`details.yaml` matches deployed config: id=arcface-resnet100, k8s_name=arcface,
type=face, embedding_dimensions=512 (verified), gpu=false.
