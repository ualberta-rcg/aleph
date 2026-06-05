# MedSAM — Medical Image Segmentation

## Source
- HuggingFace: https://huggingface.co/flaviagiammarino/medsam-vit-base
- License: Apache 2.0

## Deployment Summary
- **Model**: MedSAM ViT-Base (~375M params)
- **GPU**: 1x L40S (shared), falls back to CPU
- **PVC**: medsam-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/science/segment` — segment medical image given bounding box prompt
- Input: image (HxW RGB array), boxes (bounding box coordinates)
- Output: masks (binary segmentation), scores (confidence)

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC (all-in-one)
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- transformers (SamModel, SamProcessor)
- torch
- fastapi, uvicorn

## Gateway Integration
- ISVC name: `medsam`
- MODEL_TYPE: segment
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: not listed (should be added)

## Audit Notes
- Requires bounding box prompt (not fully automatic)
- Based on SAM ViT-Base, fine-tuned on medical data
- 8877 downloads on HuggingFace

## Update Reminder
- Check for MedSAM v2 or larger variants
- Consider adding automatic bounding box generation
