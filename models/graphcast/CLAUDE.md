# GraphCast-Small — DeepMind Weather Prediction Model

## Source
- GitHub: https://github.com/google-deepmind/graphcast
- Weights: shermansiu/dm_graphcast_small (HuggingFace)
- Stats: gs://dm_graphcast/stats/ (public GCS)
- License: CC BY-NC-SA 4.0

## Deployment Summary
- **Model**: GraphCast-Small (1-degree, 13 pressure levels, mesh 2to5)
- **GPU**: Node selector for L40S-SHARED but JAX_PLATFORMS=cpu
- **PVC**: graphcast-data (5Gi, NFS, inline in inferenceservice.yaml)
- **Scale-to-zero**: Yes (minReplicas: 0, RawDeployment)
- **Venv**: No (pip install on every start)

## API
- `GET /v1/science/info` — model config and variable list
- `POST /v1/science/predict` — demo mode only (`{"demo": true}`)
- Full ERA5 inference not yet implemented via API

## Key Files
- `inferenceservice.yaml` — ConfigMap + ISVC + PVC (all in one file)
- `details.yaml` — model metadata ConfigMap
- No separate pvc.yaml or kustomization.yaml

## Dependencies
- JAX, jaxlib, dm-haiku, chex, optax
- xarray, netCDF4, pandas, scipy, trimesh, networkx
- graphcast (installed from GitHub)
- dask, fastapi, uvicorn

## Audit Notes
- PVC defined inline in inferenceservice.yaml (no separate pvc.yaml)
- No kustomization.yaml file exists
- JAX_PLATFORMS=cpu forces CPU inference despite GPU node selector
- Normalization stats downloaded from GCS (mean, stddev, diffs_stddev)
- Full inference pipeline not yet implemented (demo/info mode only)
- Large dependency footprint (many JAX/scientific packages)

## Update Reminder
- Implement full ERA5 inference pipeline via API
- Consider enabling GPU via JAX_PLATFORMS=cuda
- Add separate pvc.yaml and kustomization.yaml for consistency
- Monitor google-deepmind/graphcast for newer model versions
