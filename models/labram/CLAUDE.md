# LaBraM — Large Brain Model for EEG Signals

## Source
- HuggingFace: https://huggingface.co/braindecode/labram-pretrained
- License: BSD-3-Clause

## Deployment Summary
- **Model**: LaBraM pretrained (braindecode)
- **GPU**: CPU-only
- **PVC**: labram-data (5Gi, RWO, inline in ISVC)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/science/embed` — EEG signals to patch embeddings
- Input: multi-channel EEG array [n_channels, n_times], sampling frequency
- Output: patch embeddings + metadata

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + PVC (all in one file)
- `details.yaml` — model metadata ConfigMap
- No separate pvc.yaml (PVC inline in ISVC)

## Dependencies
- torch (CPU)
- braindecode, safetensors, huggingface_hub
- fastapi, uvicorn

## Audit Notes
- Uses braindecode Labram.from_pretrained() API
- HF_HUB_OFFLINE=1 — requires model pre-downloaded to PVC
- CPU-only, low resource (4Gi memory)
- EEG segment length: 200 samples default
- Outputs last_hidden_state[:, 0] (CLS token) or raw output

## Update Reminder
- Monitor braindecode for model updates
- Consider adding downstream task endpoints (sleep staging, BCI)
- Add separate pvc.yaml and kustomization.yaml
