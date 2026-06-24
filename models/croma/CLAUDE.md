# CROMA — Cross-Modal Remote Sensing Foundation Model

## Source
- HuggingFace: https://huggingface.co/antofuller/CROMA
- GitHub: https://github.com/antofuller/CROMA
- License: MIT

## Deployment Summary
- **Model**: CROMA-base (~300M)
- **GPU**: 1x L40S HAMi slice
- **PVC**: `croma-data` (RWX, nfs-models) — separate `pvc.yaml`
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/embeddings` — SAR and/or optical satellite images to embeddings
- Input: sar_images [2, H, W], optical_images [12, H, W], modality selection
- Output: GAP-pooled embeddings (joint/optical/SAR) in OpenAI-compatible format
- Supports SAR-only, optical-only, or both modalities

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + init container
- `details.yaml` — model card (schema v2)
- `pvc.yaml` — PVC `croma-data` (RWX, nfs-models)
- `test.py` — ~10-check gateway battery. Run externally:
  `GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/croma/test.py`

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
- v2 deep pass 2026-06-24: schema v2 + input_map/output_map; test.py expanded to ~10 checks (0 FAIL).
