# ClimaX — Microsoft Climate Foundation Model

## Source
- GitHub: https://github.com/microsoft/ClimaX
- HuggingFace: microsoft/ClimaX (checkpoints)
- License: MIT

## Deployment Summary
- **Model**: ClimaX 108M (ViT, 5.625deg checkpoint)
- **GPU**: 1x L40S (shared)
- **PVC**: climax-data (5Gi, NFS ReadWriteMany)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/science/forecast` — weather/climate forecast
- Input: variable names + gridded data + lead time
- Output: forecast grids for requested variables

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + init container
- `pvc.yaml` — climax-data PVC (5Gi NFS)
- `details.yaml` — model metadata ConfigMap

## Dependencies
- torch + torchvision (CUDA 12.6)
- timm==0.6.13 (pinned for compatibility)
- einops, fastapi, uvicorn, huggingface_hub
- ClimaX repo cloned from GitHub to /data/model/repo

## Audit Notes
- numpy 1.24+ compatibility: pos_embed.py patched (np.float -> float)
- Two checkpoints available: 5.625deg (default) and 1.40625deg
- 48 default variables covering surface + atmospheric levels
- Repo cloned at setup time for model code (climax.arch module)

## Update Reminder
- Monitor https://github.com/microsoft/ClimaX for updates
- timm==0.6.13 is pinned; check compatibility when upgrading
- Consider adding higher-resolution 1.40625deg as default when GPU memory allows
