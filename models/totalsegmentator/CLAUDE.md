# TotalSegmentator — CT Scan Anatomical Segmentation

## Source
- GitHub: https://github.com/wasserth/TotalSegmentator
- License: Apache 2.0

## Deployment Summary
- **Model**: TotalSegmentator (~31M params, nnU-Net based)
- **GPU**: 1x L40S (shared)
- **PVC**: totalsegmentator-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/science/segment` — segment 117 anatomical structures in CT scan
- Input: ct_array (3D HU values), spacing, fast mode
- Output: segmentation labels, structure names

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + PVC + ISVC (all-in-one)
- `pvc.yaml` — totalsegmentator-data PVC
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- totalsegmentator (pip, auto-downloads nnU-Net weights)
- PyTorch, nnU-Net
- fastapi, uvicorn

## Gateway Integration
- ISVC name: `totalsegmentator`
- MODEL_TYPE: segment
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: yes
- Listed in MODEL_METADATA

## Audit Notes
- Segments 117 anatomical structures in one pass
- Uses TOTALSEGMENTATOR_HOME env var for weight caching
- Supports fast mode for quicker inference
- Clinical-grade accuracy, widely cited

## Update Reminder
- Check for new TotalSegmentator versions (new structures added)
- Monitor wasserth/TotalSegmentator for updates
