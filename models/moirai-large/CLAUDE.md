# moirai-large — Salesforce Moirai 1.1-R-Large (311M)

## Source
- HuggingFace: https://huggingface.co/Salesforce/moirai-1.1-R-large
- License: Apache-2.0
- Architecture: Moirai 1.1-R patch-based transformer (auto patch size), 311M, fp32; any-variate

## Serving contract (research 2026-06-28)
- **Install:** `uni2ts` + torch + GluonTS (`PandasDataset`) + fastapi/uvicorn. Persisted venv on PVC.
- **Weights:** `Salesforce/moirai-1.1-R-large` → `/data`. MoiraiForecast pipeline, prediction_length
  per-request, `num_samples` for quantile estimation.
- **API:** `POST /v1/science/forecast` {context, prediction_length?, freq?, num_samples?} →
  {mean (len=prediction_length), quantiles {0.1,0.5,0.9}, prediction_length, model}.
  Server reads `context` (the series); `model` is the gateway routing id.
- Distinct from `moirai` (the base ~91M model, /v1/forecast) — this is the large 311M variant on
  /v1/science/forecast.

## Deployment (standardized)
- **Pattern:** caduceus — ConfigMap `moirai-large-server` (server.py embedded) mounted read-only at
  `/app`; initContainer builds `/data/venv` + loads model (gated); main container runs the venv python.
  `/health` probes. Dropped the vestigial `kustomization.yaml` (server was already embedded).
- **PVC:** standalone `pvc.yaml`, name `moirai-large` (was `moirai-large-data`), RWX `nfs-models`.
- **GPU:** 1× L40S HAMi slice; nodeSelector `gpu=on`.
- **Scale-to-zero:** `minReplicas: 0`, 15m idle retention. **`progress-deadline: 1800s`** — the uni2ts
  venv install is slow (same lesson as moirai; without it the first deploy RevisionFailed).
- **Card:** v2 Template B (`schema_version: 2`).

## Files
- `details.yaml` (v2, `moirai-large-details`) · `inferenceservice.yaml` (ConfigMap + ISVC) ·
  `pvc.yaml` (`moirai-large`) · `test.py` (96-pt series → mean+quantiles) · `README.md`.
