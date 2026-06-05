# YOLOv8 Nano (`yolov8n`)

Ultralytics YOLOv8 Nano object detection model exported to ONNX.

## Model Information

| Property | Value |
|----------|-------|
| Source | [Ultralytics YOLOv8n](https://github.com/ultralytics/ultralytics) |
| Type | Object Detection |
| Parameters | Nano |
| Runtime | Custom FastAPI + ONNX Runtime |
| Deployment | CPU predictor with ONNX model cached on PVC |

## API Endpoint

- Gateway (`/serving/api`): `POST /v1/vision/detect`
- Direct service route: `/v1/vision/detect`
- Method: `POST`

## Example Usage

```bash
curl -X POST "https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/vision/detect" \
  -H "Content-Type: application/json" \
  -d '{"model":"yolov8n","image":"<base64_png>"}'
```

```bash
curl -X POST "https://kubeflow.vulcan.alliancecan.ca/serving/models/yolov8n/v1/vision/detect" \
  -H "Content-Type: application/json" \
  -d '{"model":"yolov8n","image":"<base64_png>"}'
```

## Resource Requirements

| Resource | Request | Limit |
|----------|---------|-------|
| CPU | 2 | 4 |
| Memory | 2Gi | 4Gi |
| GPU | None | None |
| Storage | 2Gi | - |

## Scaling Configuration

| Setting | Value |
|---------|-------|
| minReplicas | 1 |
| scale-to-zero | No |
| timeout | 600s |

## Files

| File | Purpose |
|------|---------|
| `pvc.yaml` | `yolov8n-data` dedicated PVC |
| `configmap.yaml` | Vision server config (`vision_server.py`) |
| `inferenceservice.yaml` | KServe predictor spec |
| `kustomization.yaml` | Kustomize bundle |
| `vision_server.py` | Local copy of server logic used to build config |

