# SatMAE — Masked Autoencoder for Satellite Imagery

## Source
- HuggingFace: https://huggingface.co/MVRL/satmae-vitlarge-fmow-pretrain-800
- License: Apache 2.0

## Deployment Summary
- **Model**: SatMAE ViT-Large (pretrained on fMoW)
- **GPU**: CPU-only
- **PVC**: satmae-data (5Gi, RWO, inline in ISVC)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/science/embed` — satellite image to CLS + patch embeddings
- Input: HxW RGB image (values 0-255, auto-resized to 224x224)
- Output: CLS embedding + patch embeddings

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + PVC (all in one file)
- `details.yaml` — model metadata ConfigMap
- No separate pvc.yaml (PVC inline in ISVC)

## Dependencies
- torch + torchvision (CPU)
- safetensors, timm, huggingface_hub
- fastapi, uvicorn

## Audit Notes
- Model loaded via MaskedAutoencoderViT.from_pretrained()
- fMoW normalization applied: mean=[0.4182, 0.4215, 0.3991], std=[0.2877, 0.2754, 0.2764]
- mask_ratio=0 for full embedding extraction (no masking at inference)
- HF_HUB_OFFLINE=1 — model must be pre-downloaded to PVC
- Auto-resizes non-224x224 inputs via bilinear interpolation

## Update Reminder
- Monitor MVRL for multi-spectral or temporal SatMAE variants
- Consider adding classification fine-tuning heads
- Could add GPU for faster batch processing
- Add separate pvc.yaml and kustomization.yaml
