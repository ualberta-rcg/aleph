# YOLOv8 Small (`yolov8s`)

Ultralytics YOLOv8 Small object detection model exported to ONNX.

## Model Information

| Property | Value |
|----------|-------|
| Source | [Ultralytics YOLOv8s](https://github.com/ultralytics/ultralytics) |
| Type | Object Detection |
| Parameters | Small |
| Runtime | Custom FastAPI + ONNX Runtime |
| Deployment | CPU predictor with ONNX model cached on PVC |

## API Endpoint

- Gateway (`/serving/api`): `POST /v1/vision/detect`
- Direct service route: `/v1/vision/detect`
- Method: `POST`

## Example Usage

```bash
curl -X POST "http://<GATEWAY_VIP>/v1/vision/detect" \
  -H "Authorization: Bearer <TYK_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"model":"yolov8s","image":"<base64_png>"}'
```

Run the full test battery externally:

```bash
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/yolov8s/test.py
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
| `pvc.yaml` | `yolov8s-data` dedicated PVC |
| `configmap.yaml` | Vision server config (`vision_server.py`) |
| `inferenceservice.yaml` | KServe predictor spec |
| `vision_server.py` | Local copy of server logic used to build config |

## HF / upstream I/O reference

- Source: <https://docs.ultralytics.com/models/yolov8/>
- Task family: COCO object detection (YOLOv8s, 80 classes).
- Input: base64 RGB image.
- Output: `detections[]` with `{label, score, box}`.

