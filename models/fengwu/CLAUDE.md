# FengWu v2 — Shanghai AI Lab Global Weather Forecast

## Source
- HuggingFace: https://huggingface.co/OpenEarthLab/FengWu
- Weights: PaddleScience CDN (paddle-org.bj.bcebos.com)
- License: Apache 2.0

## Deployment Summary
- **Model**: FengWu v2 ONNX (~1.9GB)
- **GPU**: 1x L40S (dedicated)
- **PVC**: fengwu-data (10Gi, NFS ReadWriteMany)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: No (uses python:3.11 base image, pip install on every start)

## API
- `POST /v1/science/forecast` — 6h global weather forecast
- Input: surface (4, 721, 1440) + upper (5, 13, 721, 1440) ERA5 arrays
- Output: same shape arrays for next 6h step
- Demo mode: `{"demo": true}` returns zeroed arrays

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + init container
- `pvc.yaml` — fengwu-data PVC (10Gi NFS)
- `details.yaml` — model metadata ConfigMap

## Dependencies
- onnxruntime-gpu >= 1.18
- fastapi, uvicorn

## Audit Notes
- No venv pattern — pip installs on every container start (could be optimized)
- Sentinel file: /data/.fengwu-ready-v1
- ONNX model downloaded from PaddleScience CDN (~1.9GB)
- Same input/output format as pangu-weather
- Large memory: 16Gi request / 32Gi limit (for 721x1440 arrays)

## Update Reminder
- Consider migrating to venv-on-PVC pattern for faster cold starts
- Monitor OpenEarthLab/FengWu for newer model versions
- Could share inference code with pangu-weather (same ONNX pattern)
