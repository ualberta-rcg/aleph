# Mask R-CNN ResNet-50 — Model Context

## What This Model Does

Mask R-CNN ResNet-50 FPN v2 from torchvision. 46.4M params. Two-stage instance segmentation: detects objects and generates per-instance binary segmentation masks. 80 COCO classes (person, car, dog, etc.). Runs on CPU via PyTorch with torchvision weights (no ONNX). Returns bounding boxes with class labels, confidence scores. 47.4 mAP@50-95 on COCO.

## Source Repo

**Docs**: [PyTorch Mask R-CNN](https://pytorch.org/vision/stable/models/mask_rcnn.html)
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
- **ConfigMap**: `maskrcnn-server` — server code embedded in inferenceservice.yaml
- **PVC**: `maskrcnn-data` — stores venv only (5Gi, NFS ReadWriteMany)
- **Health**: Custom `/health` endpoint
- **CPU only**: No GPU allocation. PyTorch CPU inference.
- **Env vars**: `MODEL_NAME=maskrcnn-resnet50`
- **No model download**: Weights are downloaded by torchvision on first load from internal CDN

## Gateway Integration

- **k8s ISVC name**: `maskrcnn`
- **API model ID**: `maskrcnn-resnet50` (mapped via ISVC_NAME_MAP)
- **MODEL_TYPE**: segment
- **KSERVE_CUSTOM_MODELS**: yes — uses `/v1/` prefix
- **Scale-to-zero**: minReplicas=0, scaleTarget=2, 900s retention

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/maskrcnn/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=maskrcnn

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=maskrcnn -c kserve-container -f

# Test (public) — need a base64-encoded image
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/vision/segment \
  -H "Content-Type: application/json" \
  -d '{"model":"maskrcnn-resnet50","image":"<base64_encoded_jpeg>"}'
```

## Known Issues / Optimization Opportunities

1. **CPU only**: Model runs on CPU with PyTorch. Instance segmentation is computationally expensive — GPU would provide major speedup.

2. **No ONNX**: Uses PyTorch directly. Could export to ONNX for faster inference.

3. **No image resizing**: Server processes images at native resolution. Large images will be slow.

4. **Hardcoded CONF_THRESH**: Confidence threshold is hardcoded at 0.5 in server code. Should be configurable via env var.

5. **Pip dependencies unpinned**: Init container installs deps without version pins.

6. **No model download step**: Weights are loaded by torchvision at runtime, making first request slow.

7. **Mask output**: Server returns bounding boxes but does NOT return the actual segmentation mask pixels. The raw mask tensors are available from torchvision but not serialized in the response. Could be added as base64 PNGs.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap + ISVC spec: init container + FastAPI container |
| `kustomization.yaml` | Kustomize resources |
| `pvc.yaml` | Dedicated PVC (maskrcnn-data) |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**

## HF / upstream I/O reference
- Source: https://pytorch.org/vision/stable/models/mask_rcnn.html
- Runtime mapping used here: base64 image in -> `detections[{label,score,box}]` out on `/v1/vision/segment`.
