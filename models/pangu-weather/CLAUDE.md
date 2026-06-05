# Pangu-Weather — Huawei 3D Neural Network Weather Forecast

## Source
- GitHub: https://github.com/SpuriousCorrelations/Pangu-Weather
- Weights: ECMWF CDN (get.ecmwf.int)
- License: BY-NC-SA 4.0

## Deployment Summary
- **Model**: Pangu-Weather 6-hour ONNX (~1.1GB)
- **GPU**: 1x L40S (shared)
- **PVC**: pangu-weather-data (10Gi, ReadWriteOnce)
- **Scale-to-zero**: Yes (minReplicas: 0, RawDeployment)
- **Venv**: Yes (/data/venv-v4 on PVC)

## API
- `POST /v1/science/forecast` — 6h global weather forecast
- Input: base64-encoded numpy arrays (upper: 5x13x721x1440, surface: 4x721x1440)
- Output: forecast arrays + summary stats + sample T850
- Demo mode: `{"demo": true}` uses synthetic data

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + init container
- `pvc.yaml` — pangu-weather-data PVC (10Gi RWO)
- `details.yaml` — model metadata ConfigMap

## Dependencies
- onnxruntime-gpu >= 1.18
- numpy, fastapi, uvicorn[standard]

## Audit Notes
- Uses atomic mkdir lock for NFS-safe setup (LOCKDIR pattern)
- Venv at /data/venv-v4 (versioned path)
- ONNX model from ECMWF CDN (~1.1GB)
- Arena memory settings tuned for ONNX (no mem arena, no pattern, no reuse)
- 13 pressure levels: 50-1000 hPa
- Returns sample_t850_K (8x8 corner) for quick verification

## Update Reminder
- Monitor for 24h and other timestep ONNX models
- Consider adding 24-hour model alongside 6-hour
- Same input format as fengwu — could share infrastructure
