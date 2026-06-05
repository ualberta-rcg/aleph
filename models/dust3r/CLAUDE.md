# DUSt3R — Unconstrained 3D Reconstruction from Images

## Source
- HuggingFace: https://huggingface.co/naver/DUSt3R_ViTLarge_BaseDecoder_512_dpt
- Paper: CVPR 2024
- License: CC-BY-NC-4.0 (non-commercial)

## Deployment Summary
- **Model**: DUSt3R ViTLarge_BaseDecoder_512_dpt (~300M params)
- **GPU**: 1x L40S (shared)
- **PVC**: dust3r-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/science/reconstruct` — 3D reconstruction from 2+ images
- Input: base64-encoded images (no calibration needed)
- Output: 3D point clouds with confidence maps

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + PVC + ISVC (all-in-one)
- `pvc.yaml` — dust3r-data PVC
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- dust3r (cloned repo with custom model code)
- torch (CUDA)
- fastapi, uvicorn

## Gateway Integration
- ISVC name: `dust3r`
- MODEL_TYPE: 3d
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: yes
- Listed in MODEL_METADATA

## Audit Notes
- Requires cloned GitHub repo for model code (not pip-installable)
- CC-BY-NC-4.0 license (non-commercial)
- No camera calibration required — truly unconstrained
- Uses sys.path insertion for repo code access

## Update Reminder
- Check for DUSt3R v2 or improved checkpoints
- Monitor naver/dust3r for updates
