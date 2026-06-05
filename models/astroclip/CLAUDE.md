# AstroCLIP — Cross-Modal Galaxy Image + Spectrum CLIP

## Source
- HuggingFace: https://huggingface.co/polymathic-ai/astroclip
- GitHub: https://github.com/polymathic-ai/astroclip
- License: MIT

## Deployment Summary
- **Model**: AstroCLIP (~1.7GB Lightning checkpoint)
- **GPU**: 1x L40S (dedicated)
- **PVC**: astroclip-data (inline in ISVC)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: No (pip install on every start)

## API
- `POST /v1/science/embed` — galaxy image or spectrum to 512-dim embedding
- Supports two modalities: image (H,W,3) and spectrum (wavelength_bins,)
- Demo mode: returns zero 512-dim embedding

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + init container
- `details.yaml` — model metadata ConfigMap
- No separate pvc.yaml (PVC inline in ISVC)

## Dependencies
- torch + torchvision (CUDA 12.6)
- lightning, fastapi, uvicorn
- astroclip repo cloned from GitHub

## Audit Notes
- Checkpoint key patching: dino. prefix removed from state dict
- Falls back to raw checkpoint demo mode if library unavailable
- Sentinel file: /data/.astroclip-ready-v1
- Cross-modal: can embed both images and spectra into same space
- 512-dim joint embedding for cross-modal retrieval

## Update Reminder
- Monitor polymathic-ai/astroclip for updated checkpoints
- Add separate pvc.yaml for consistency
- Consider adding cross-modal retrieval endpoint
