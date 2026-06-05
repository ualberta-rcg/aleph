# Sundial — Model Context

## What This Model Does

Sundial by THUML (Tsinghua). 128M params. Generative time series foundation model for zero-shot probabilistic forecasting. Autoregressive generation with normalization-aware inference. Supports arbitrary horizon lengths and multi-sample probabilistic outputs. CPU-capable with no GPU required. Apache 2.0 license. 1M+ HuggingFace downloads.

## Source Repo

**HuggingFace**: [thuml/sundial-base-128m](https://huggingface.co/thuml/sundial-base-128m)

Key info from source:
- **Input format**: Array of numeric time series values
- **Horizon**: Configurable (default 96)
- **License**: Apache-2.0
- **Architecture**: Causal LM (128M params)
- **CPU capable**: No GPU required

## How The Server Works

- **Pattern**: Custom FastAPI forecast server with HuggingFace Transformers (trust_remote_code)
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`
- **Init container**: Creates venv, installs torch+transformers (CPU), downloads model from HF to PVC
- **ConfigMap**: `sundial-server` — server code embedded in inferenceservice.yaml
- **PVC**: `sundial-data` — stores venv + model weights (10Gi)
- **Health**: Custom `/health` endpoint
- **CPU only**: No GPU allocation. PyTorch CPU with float32.
- **Env vars**: `MODEL_DIR=/data/model`, `HF_HUB_OFFLINE=1`
- **Output**: Custom `/v1/science/forecast` response format with probabilistic forecasts
- **Note**: Uses venv-on-PVC pattern, trust_remote_code=True for model loading

## Gateway Integration

- **k8s ISVC name**: `sundial`
- **API model ID**: `sundial` (no mapping in ISVC_NAME_MAP)
- **MODEL_TYPE**: defaults to "chat" — needs update to "forecast"
- **KSERVE_CUSTOM_MODELS**: not listed — needs addition
- **Scale-to-zero**: minReplicas=0, scaleTarget=2, 900s retention

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/sundial/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=sundial

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=sundial -c kserve-container -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/science/forecast \
  -H "Content-Type: application/json" \
  -d '{"model":"sundial","series":[1.2,1.5,1.8,2.1,2.4,2.7,3.0,3.3,3.6,3.9],"horizon":5,"num_samples":10}'
```

## Known Issues / Optimization Opportunities

1. **trust_remote_code=True**: Executes arbitrary code from HF repo. Verify model source integrity.

2. **High CPU/memory requests**: 4 CPU / 8Gi RAM is generous for 128M model. Could reduce.

3. **Z-score normalization in inference**: Series normalized per-request. May produce poor results for very short or constant series.

4. **No PVC storageClassName**: PVC missing storageClassName.

5. **Gateway registration incomplete**: Model not in MODEL_TYPES, MODEL_METADATA, KSERVE_CUSTOM_MODELS, or CONTEXT_WINDOWS in gateway.py.

6. **timeout 300s**: Long timeout for large horizons. Appropriate but may cause issues with load balancers.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap + PVC + ISVC spec |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
