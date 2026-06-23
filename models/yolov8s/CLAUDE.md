# yolov8s

**Type**: Object detection (ONNX, CPU)
**Model**: YOLOv8s (Ultralytics, COCO 80-class, ~11M params)
**Endpoint**: POST /v1/vision/detect
**Runtime**: CPU, ONNX Runtime, venv on PVC

## Migration notes
- Same pattern as yolov8n. Already Knative + scale-to-zero + nfs-models PVC.
- Only change: added `routing.k8s_name: yolov8s` to details.yaml.
- Init exports `yolov8s.pt` → `yolov8s.onnx`.

## Validation
- POST /v1/vision/detect with 1×1 white PNG → empty detections. PASS.
- Catalog: id=yolov8s, type=detect, endpoint=/v1/vision/detect. PASS.
