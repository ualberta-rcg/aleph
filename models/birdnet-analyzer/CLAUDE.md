# BirdNET-Analyzer — Cornell Lab Bird Species Identification

## Source
- GitHub: https://github.com/kahst/BirdNET-Analyzer
- License: CC-BY-NC-SA-4.0

## Deployment Summary
- **Model**: BirdNET-Analyzer (~15M params)
- **GPU**: 1x L40S (shared)
- **PVC**: birdnet-analyzer-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/science/identify` — identify bird species from audio
- Input: audio samples (float32 at 48kHz), lat, lon, week, min_confidence
- Output: detections with species, common name, confidence, time segments

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + PVC + ISVC (all-in-one)
- `pvc.yaml` — birdnet-analyzer-data PVC
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- birdnetlib (handles model download internally)
- TensorFlow/TFLite (runtime)
- fastapi, uvicorn

## Gateway Integration
- ISVC name: `birdnet-analyzer`
- MODEL_TYPE: classify
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: yes
- Listed in MODEL_METADATA

## Audit Notes
- birdnetlib handles model download and caching internally
- Supports 6000+ bird species
- Location and season filtering reduce false positives
- CC-BY-NC-SA-4.0 license (non-commercial, share-alike)

## Update Reminder
- Check for BirdNET model updates (new species added regularly)
- Monitor birdnetlib package for API changes
