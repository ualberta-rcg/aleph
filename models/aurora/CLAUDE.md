# Aurora — Microsoft Atmospheric Foundation Model

## Source
- HuggingFace: https://huggingface.co/microsoft/aurora
- Paper: Nature 2025
- License: MIT

## Deployment Summary
- **Model**: Aurora 0.25-small-pretrained (1.3B params)
- **GPU**: 1x L40S (shared)
- **PVC**: aurora-data (15Gi, NFS ReadWriteMany)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/science/forecast` — global weather forecast 6h ahead
- Input: surface vars (2t, 10u, 10v, msl) + atmospheric vars (t, u, v, q, z) at 13 pressure levels
- Output: same structure for next 6-hour step

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + init container
- `pvc.yaml` — aurora-data PVC (15Gi NFS)
- `details.yaml` — model metadata ConfigMap

## Dependencies
- microsoft-aurora (pip)
- torch + torchvision (CUDA 12.6)
- fastapi, uvicorn, huggingface_hub

## Audit Notes
- Static variables (aurora-0.25-static.pickle) interpolated to input grid size at runtime
- Checkpoint downloaded via HF hub to PVC HF cache
- Sentinel file: /data/model/aurora-ready-v2

## Update Reminder
- Check for new Aurora checkpoint releases (larger models, higher resolution)
- Monitor microsoft/aurora HF repo for version updates
- Verify torchvision compatibility when upgrading torch
