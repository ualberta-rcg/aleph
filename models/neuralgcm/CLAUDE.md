# NeuralGCM — Google DeepMind Hybrid Physics/ML Atmospheric Model

## Source
- GitHub: https://github.com/google-deepmind/neuralgcm
- Weights: gs://neuralgcm/models/v1/ (public GCS)
- License: CC-BY-SA 4.0

## Deployment Summary
- **Model**: NeuralGCM v1 deterministic 2.8-degree
- **GPU**: Node selector L40S-SHARED but JAX_PLATFORMS=cpu
- **PVC**: neuralgcm-data (2Gi, NFS, inline in inferenceservice.yaml)
- **Scale-to-zero**: Yes (minReplicas: 0, RawDeployment)
- **Venv**: No (pip install on every start)

## API
- `GET /v1/science/info` — model config and capabilities
- `POST /v1/science/predict` — demo mode only (`{"demo": true}`)
- Full inference not yet implemented

## Key Files
- `inferenceservice.yaml` — ConfigMap + ISVC + PVC (all in one file)
- `details.yaml` — model metadata ConfigMap
- No separate pvc.yaml or kustomization.yaml

## Dependencies
- neuralgcm, jax, jaxlib, gcsfs, dm-haiku
- fastapi, uvicorn

## Audit Notes
- Checkpoint serialized as pickle from GCS
- JAX_PLATFORMS=cpu forces CPU mode
- Demo mode only — real inference pipeline not yet implemented
- No separate kustomization.yaml
- Small PVC (2Gi) — only for checkpoint

## Update Reminder
- Implement full inference pipeline for ERA5 inputs
- Consider enabling GPU for faster inference
- Add separate pvc.yaml and kustomization.yaml
- Also available: 1.4-degree and 0.7-degree variants
- Stochastic variants available for ensemble forecasting
