# MASt3R — Grounding Image Matching in 3D

## Source
- HuggingFace: https://huggingface.co/naver/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric
- Paper: ECCV 2024
- License: CC-BY-NC-4.0 (non-commercial)

## Deployment Summary
- **Model**: MASt3R ViTLarge_BaseDecoder_512_catmlpdpt_metric (~300M params)
- **GPU**: 1x L40S (shared)
- **PVC**: mast3r-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/science/reconstruct` — 3D scene reconstruction from images
- `POST /v1/science/match` — feature matching between 2 images
- Input: base64-encoded images
- Output: 3D correspondences, metric depth

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + PVC + ISVC (all-in-one)
- `pvc.yaml` — mast3r-data PVC
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- mast3r (cloned repo)
- dust3r (submodule of mast3r repo)
- torch (CUDA)

## Gateway Integration
- ISVC name: `mast3r`
- MODEL_TYPE: 3d
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: yes
- Listed in MODEL_METADATA

## Audit Notes
- Extends DUSt3R with metric depth and feature matching
- Requires both mast3r and dust3r repos in sys.path
- CC-BY-NC-4.0 license (non-commercial)
- State-of-the-art for visual localization tasks

## Update Reminder
- Check for MASt3R v2 releases
- Monitor naver/mast3r for updates
