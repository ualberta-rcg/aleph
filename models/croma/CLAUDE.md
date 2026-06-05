# CROMA — Cross-Modal Remote Sensing Foundation Model

## Source
- HuggingFace: https://huggingface.co/antofuller/CROMA
- GitHub: https://github.com/antofuller/CROMA
- License: MIT

## Deployment Summary
- **Model**: CROMA-base (~300M)
- **GPU**: 1x L40S (shared)
- **PVC**: croma-data (5Gi, NFS, inline in ISVC)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/embeddings` — SAR and/or optical satellite images to embeddings
- Input: sar_images [2, H, W], optical_images [12, H, W], modality selection
- Output: per-patch embeddings in OpenAI-compatible format
- Supports SAR-only, optical-only, or both modalities

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + init container
- `details.yaml` — model metadata ConfigMap
- No separate pvc.yaml (PVC inline in ISVC)

## Dependencies
- torch + torchvision (CUDA 12.6)
- einops, timm, fastapi, uvicorn, huggingface_hub
- CROMA repo cloned from GitHub for inference code

## Audit Notes
- Uses PretrainedCROMA class from repo's use_croma.py
- Image resolution fixed at 120x120
- SAR input: 2 channels (VV, VH from Sentinel-1)
- Optical input: 12 channels (Sentinel-2 MSI bands)
- Gateway type: segment (per gateway.py MODEL_TYPES)

## Update Reminder
- Monitor antofuller/CROMA for updated checkpoints
- Consider adding segmentation/classification endpoints
- Add separate pvc.yaml for consistency
