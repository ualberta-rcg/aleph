# MegaDetector — Microsoft Wildlife Camera Trap Detector

## Source
- GitHub: https://github.com/microsoft/CameraTraps
- License: MIT

## Deployment Summary
- **Model**: MegaDetector v5a (~87M params, YOLOv5)
- **GPU**: 1x L40S (shared)
- **PVC**: megadetector-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/detect` — detect animals, humans, vehicles in camera trap images
- Input: images (base64 array), confidence threshold
- Output: detections with category, bbox, confidence

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + PVC + ISVC (all-in-one)
- `pvc.yaml` — megadetector-data PVC
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- megadetector (pip)
- PyTorch
- fastapi, uvicorn

## Gateway Integration
- ISVC name: `megadetector`
- MODEL_TYPE: detect
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: yes
- Listed in MODEL_METADATA

## Audit Notes
- 3 categories: animal, human, vehicle
- Bounding boxes are normalized [0,1]
- Falls back to MDV5A if local checkpoint not found
- Widely used in conservation biology worldwide

## Update Reminder
- Check for MegaDetector v6 releases
- Monitor microsoft/CameraTraps for updates
