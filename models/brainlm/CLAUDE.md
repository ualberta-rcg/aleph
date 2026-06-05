# BrainLM — fMRI Foundation Model

## Source
- HuggingFace: https://huggingface.co/vandijklab/BrainLM
- Paper: ICLR 2024
- License: MIT

## Deployment Summary
- **Model**: BrainLM 650M (ViT-MAE architecture)
- **GPU**: 1x L40S (shared)
- **PVC**: brainlm-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/embeddings` — encode fMRI time-series into 768-dim embeddings
- Input: fMRI data [424 ROIs x timepoints]
- Output: 768-dimensional latent embeddings

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + PVC + ISVC (all-in-one)
- `pvc.yaml` — brainlm-data PVC
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- transformers (ViTMAEForPreTraining, ViTMAEConfig)
- torch
- fastapi, uvicorn

## Gateway Integration
- ISVC name: `brainlm`
- MODEL_TYPE: embed
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: yes
- Listed in MODEL_METADATA

## Audit Notes
- Adapted ViT-MAE (vision model) for fMRI time-series data
- Requires exactly 424 ROI inputs (UK Biobank parcellation)
- Custom weight loading with ViTMAEConfig from config.json
- Trained on 6,700 hours of fMRI data

## Update Reminder
- Check for BrainLM v2 or larger variants
- Monitor vandijklab/BrainLM for updates
