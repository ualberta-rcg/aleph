# RetinaNet ResNet-50 — Model Context

## What This Model Does

RetinaNet ResNet-50 FPN v2 from torchvision. 37.7M params. Single-stage object detector using focal loss for dense detection. 80 COCO classes (person, car, dog, etc.). Runs on CPU via PyTorch with torchvision weights (no ONNX — uses `torchvision.models.detection.retinanet_resnet50_fpn_v2(weights="DEFAULT")`). Returns bounding boxes with class labels and confidence scores. 41.5 mAP@50-95 on COCO.

## Source Repo

**Docs**: [PyTorch RetinaNet](https://pytorch.org/vision/stable/models/retinanet.html)
**License**: BSD-3-Clause

Key info from source:
- **Input size**: Variable (no resizing — processes at native resolution)
- **Framework**: torchvision (PyTorch), not ONNX
- **Confidence threshold**: Hardcoded at 0.5 in server code
- **Weights**: COCO_V2 (improved over V1)

## How The Server Works

- **Pattern**: Custom FastAPI with PyTorch inference (torchvision model, NOT ONNX)
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`
- **Init container**: Creates venv, installs torch+torchvision (CPU wheels)
- **ConfigMap**: `retinanet-server` — server code embedded in inferenceservice.yaml
- **PVC**: `retinanet-data` — stores venv only (5Gi, NFS ReadWriteMany)
- **Health**: Custom `/health` endpoint
- **CPU only**: No GPU allocation. PyTorch CPU inference.
- **Env vars**: `MODEL_NAME=retinanet-resnet50`
- **No model download**: Weights are downloaded by torchvision on first load from internal CDN

## Gateway Integration

- **k8s ISVC name**: `retinanet`
- **API model ID**: `retinanet-resnet50` (mapped via ISVC_NAME_MAP)
- **MODEL_TYPE**: detect
- **KSERVE_CUSTOM_MODELS**: yes — uses `/v1/` prefix
- **Scale-to-zero**: minReplicas=0, scaleTarget=2, 900s retention

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/retinanet/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=retinanet

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=retinanet -c kserve-container -f

# Test (public) — need a base64-encoded image
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/vision/detect \
  -H "Content-Type: application/json" \
  -d '{"model":"retinanet-resnet50","image":"<base64_encoded_jpeg>"}'
```

## Known Issues / Optimization Opportunities

1. **CPU only**: Model runs on CPU with PyTorch. Could use GPU for significant speedup.

2. **No ONNX**: Unlike YOLO models, this uses PyTorch directly. Could export to ONNX for faster inference.

3. **No image resizing**: Server processes images at native resolution, which can be slow for large images.

4. **Hardcoded CONF_THRESH**: Confidence threshold is hardcoded at 0.5 in server code, not configurable via env var. Should be made configurable.

5. **Pip dependencies unpinned**: Init container installs deps without version pins.

6. **No model download step**: Weights are loaded by torchvision at runtime (not in init container). This means first request after pod start will be slow. Could pre-download in init container.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap + ISVC spec: init container + FastAPI container |
| `kustomization.yaml` | Kustomize resources |
| `pvc.yaml` | Dedicated PVC (retinanet-data) |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
