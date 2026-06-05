# efficientnet-b0

**Type**: Image classification (EfficientNet-B0, ONNX, CPU)
**Endpoint**: POST /v1/vision/classify
**Runtime**: CPU, ONNX Runtime, venv on PVC

## Migration notes
- Ported from 232. Already Knative + scale-to-zero + nfs-client PVC.
- Only change: added `routing.k8s_name: efficientnet-b0` to details.yaml.

## Validation
- POST /v1/vision/classify with 1×1 white PNG → ranked predictions (class_id, score). PASS.
- Catalog: id=efficientnet-b0, type=classify, endpoint=/v1/vision/classify. PASS.
