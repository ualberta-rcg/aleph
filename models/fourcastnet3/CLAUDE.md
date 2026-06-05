# FourCastNet3 — NVIDIA Spherical Neural Operator Weather Model

## Source
- Framework: NVIDIA earth2studio
- Weights: NVIDIA NGC (auto-downloaded)
- License: NVIDIA Software License

## Deployment Summary
- **Model**: FourCastNet3 (SFNO, 73 ERA5 variables)
- **GPU**: 1x L40S (dedicated)
- **PVC**: fourcastnet3-data (defined in ISVC, no separate pvc.yaml)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: No (pip install on every start)

## API
- `POST /v1/science/forecast` — multi-step global weather forecast
- Input: variable dict + steps count
- Output: list of per-step forecasts
- Demo mode: returns synthetic forecast data

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + init container
- `details.yaml` — model metadata ConfigMap
- No pvc.yaml (PVC defined inline in ISVC)

## Dependencies
- earth2studio (NVIDIA framework)
- torch (CUDA 12.6)
- fastapi, uvicorn

## Audit Notes
- Currently in demo mode — real inference needs full earth2studio integration
- Weights auto-downloaded from NGC on first inference
- No venv pattern — installs on every container start (slow cold starts)
- Sentinel file: /data/.fourcastnet3-ready-v1
- Duplicate `env:` key in container spec (minor YAML issue)
- Large memory footprint: 16Gi request / 32Gi limit

## Update Reminder
- Implement real inference via earth2studio rollout API
- Migrate to venv-on-PVC pattern
- Add proper PVC yaml file
- Fix duplicate env key in container spec
- Monitor NVIDIA earth2studio for API changes
