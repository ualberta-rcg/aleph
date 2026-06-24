# yolov8n

**Type**: Object detection (ONNX, CPU)
**Model**: YOLOv8n (Ultralytics, COCO 80-class)
**Endpoint**: POST /v1/vision/detect
**Runtime**: CPU, ONNX Runtime, venv on PVC

## Migration notes
- Ported from 232. Already Knative + scale-to-zero + nfs-models PVC. No GPU nodeSelector.
- Only change: added `routing.k8s_name: yolov8n` to details.yaml.
- Init container exports `yolov8n.pt` → `yolov8n.onnx` on first cold start.

## Key quirks
- Input: base64-encoded image (JPEG/PNG).
- Output: list of detections with `class_name`, `confidence`, `bbox [x1,y1,x2,y2]`.
- Model downloads `yolov8n.pt` from Ultralytics (internet required on first cold start).
- Uses OpenCV headless (opencv-python-headless) to avoid libGL dependency.

## Validation
- POST /v1/vision/detect with 1×1 white PNG → empty detections. PASS (no objects in 1×1 image).
- Catalog: id=yolov8n, type=detect, endpoint=/v1/vision/detect. PASS.

## HF / upstream I/O reference
- Source: https://docs.ultralytics.com/models/yolov8/
- Runtime mapping used here: base64 image -> `detections[{label,score,box}]` on `/v1/vision/detect`.
