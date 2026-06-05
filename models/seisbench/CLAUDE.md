# SeisBench — Seismic Phase Detection (PhaseNet)

## Source
- GitHub: https://github.com/seisbench/seisbench
- License: GPL-3.0

## Deployment Summary
- **Model**: PhaseNet (stead pretrained, ~1M params)
- **GPU**: 1x L40S (shared)
- **PVC**: seisbench-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/science/detect` — detect P/S wave arrivals in seismic data
- Input: waveforms (3-component Z,N,E), sampling_rate
- Output: detections with phase type, sample time, probability

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + PVC + ISVC (all-in-one)
- `pvc.yaml` — seisbench-data PVC
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- seisbench (includes PhaseNet model)
- PyTorch
- fastapi, uvicorn

## Gateway Integration
- ISVC name: `seisbench`
- MODEL_TYPE: classify
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: yes
- Listed in MODEL_METADATA

## Audit Notes
- Uses 'stead' pretrained variant (trained on STEAD dataset)
- Models auto-download to SEISBENCH_CACHE_ROOT
- 1D U-Net processes Z, N, E components simultaneously
- GPL-3.0 license

## Update Reminder
- Check for new PhaseNet pretrained variants
- Monitor seisbench for model updates
