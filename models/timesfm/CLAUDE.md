# TimesFM 2.0 -- Model Context

## What This Model Does

TimesFM 2.0 (google/timesfm-2.0-500m-pytorch) is Google's time-series foundation model for zero-shot forecasting. A decoder-only transformer with 50 layers, 1280 model dims, and patch-based processing (input_patch=32, output_patch=128). Supports context lengths up to 2048 time points and any prediction horizon. Returns point forecasts with optional quantile predictions. 500M parameters. Apache-2.0 license.

## Source Repo

**HuggingFace**: [google/timesfm-2.0-500m-pytorch](https://huggingface.co/google/timesfm-2.0-500m-pytorch)

- **GitHub**: [google-research/timesfm](https://github.com/google-research/timesfm)
- **License**: Apache-2.0
- **Paper**: "A decoder-only foundation model for time-series forecasting" (ICML 2024)
- **Architecture**: Patch-based decoder-only transformer
- **Fixed params**: input_patch_len=32, output_patch_len=128, num_layers=50, model_dims=1280, use_positional_embedding=False

## How The Server Works

- **Pattern**: Custom FastAPI + venv on PVC
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`
- **Init container**: Creates venv, installs torch (cu121) + transformers + numpy + fastapi + uvicorn + huggingface_hub, downloads model from HF
- **ConfigMap**: Server code embedded as `timesfm-server` ConfigMap, mounted at `/app/`
- **PVC**: `timesfm-data` (15Gi, NFS) -- stores venv + model weights
- **Health**: Custom `/health` endpoint returns `{"status": "ok|loading", "model": "timesfm", "device": "cuda|cpu"}`
- **GPU**: 1x L40S-SHARED (time-sliced), fp32 inference
- **Startup**: ~2-3 minutes

## Our Config vs Source Recommendations

| Aspect | Source | Our Config | Notes |
|--------|--------|-----------|-------|
| Library | `timesfm` Python package | `timesfm` package (standalone server.py) / `transformers` (inferenceservice.yaml) | Two server.py versions exist |
| Batch size | per_core_batch_size=32 | 1 | Single series at a time |
| Horizon | Configurable | Configurable via `horizon` param | Default 12 |
| Context length | Up to 2048 | Up to 2048 | Correct |
| Quantile heads | Experimental | Approximated if not available | Graceful fallback |
| Precision | Not specified | fp32 | Safe default |

Note: There are two different server.py implementations. The standalone `server.py` in the repo root uses the `timesfm` library directly. The one embedded in `inferenceservice.yaml` uses HuggingFace Transformers `TimesFmModelForPrediction`. The deployed version is the inferenceservice.yaml one (configMapGenerator uses the standalone file).

## Gateway Integration

- **ISVC name**: `timesfm` (maps to API id `timesfm-500m`)
- **MODEL_TYPE**: forecast
- **KSERVE_CUSTOM_MODELS**: yes -- uses `/v1/` prefix
- **GPU_MODELS**: yes
- **CONTEXT_WINDOWS**: 512
- **Scale-to-zero**: minReplicas=0, scaleTarget=3, 900s retention
- **Custom health probe**: yes (in `_CUSTOM_HEALTH_MODELS`)
- **Startup time estimate**: 2-3 minutes

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/timesfm/

# Force update
kubectl apply --server-side --force-conflicts -k models/timesfm/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=timesfm

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=timesfm -c kserve-container -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/forecast \
  -H "Content-Type: application/json" \
  -d '{"model":"timesfm-500m","values":[1.0,1.5,2.0,2.5,3.0,3.5,4.0,4.5,5.0,5.5,6.0,6.5],"horizon":6}'
```

## Known Issues / Optimization Opportunities

1. **Two server.py implementations**: The standalone `server.py` uses the `timesfm` library, while the embedded one in `inferenceservice.yaml` uses HuggingFace Transformers. This is confusing -- the configMapGenerator references the standalone file, so the `timesfm` library version is what runs in production.

2. **Pip installs on every startup**: The init container always runs pip install (no idempotent skip for the pip install step, only the model download is skipped). This adds ~1-2 minutes to every cold start.

3. **Unpinned dependencies**: All pip packages are unpinned except the model download is idempotent.

4. **Quantile approximation**: When `full_predictions` is not available, quantiles are crudely approximated as +/- 10% of mean. This is not a real quantile forecast.

5. **fp32 on GPU**: Model runs in fp32. Could use fp16 to reduce VRAM usage and speed up inference.

6. **No input length validation**: Does not warn or error if input exceeds 2048 context length.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap (server.py) + ISVC spec |
| `kustomization.yaml` | Kustomize resources + configMapGenerator |
| `pvc.yaml` | Dedicated PVC (timesfm-data, 15Gi NFS) |
| `server.py` | Extracted server code (actual code lives in ConfigMap via kustomize configMapGenerator) |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml, server.py), update details.yaml to match.**
