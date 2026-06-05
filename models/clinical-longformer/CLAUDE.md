# Clinical-Longformer — Model Context

## What This Model Does

Clinical-Longformer by yikuan8. 149M params. Longformer model pre-trained on MIMIC-III clinical notes. Handles long clinical documents up to 4096 tokens, far exceeding standard 512-token BERT models. Superior to ClinicalBERT for long clinical texts like discharge summaries and radiology reports. Apache 2.0 license.

## Source Repo

**HuggingFace**: [yikuan8/Clinical-Longformer](https://huggingface.co/yikuan8/Clinical-Longformer)

Key info from source:
- **Input format**: Clinical text strings
- **Max tokens**: 4096 (Longformer sliding window attention)
- **License**: Apache-2.0
- **Embedding dim**: 768
- **Training data**: MIMIC-III clinical notes

## How The Server Works

- **Pattern**: Custom FastAPI embedding server with HuggingFace Transformers
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`
- **Init container**: Creates venv, installs torch+transformers (CPU), downloads model from HF to PVC
- **ConfigMap**: `clinical-longformer-server` — server code embedded in inferenceservice.yaml
- **PVC**: `clinical-longformer-data` — stores venv + model weights (5Gi)
- **Health**: Custom `/health` endpoint
- **GPU**: 1x shared L40S via time-slicing
- **Env vars**: `MODEL_DIR=/data/model`, `HF_HUB_OFFLINE=1`
- **Pooling**: CLS token with global attention mask (Longformer-specific)
- **Output**: Custom `/v1/science/embed` response format

## Gateway Integration

- **k8s ISVC name**: `clinical-longformer`
- **API model ID**: `clinical-longformer` (no mapping in ISVC_NAME_MAP)
- **MODEL_TYPE**: defaults to "chat" — needs update to "embedding"
- **KSERVE_CUSTOM_MODELS**: not listed — needs addition
- **CONTEXT_WINDOWS**: should be 4096
- **Scale-to-zero**: minReplicas=0, scaleTarget=1, 10m retention

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/clinical-longformer/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=clinical-longformer

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=clinical-longformer -c kserve-container -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/science/embed \
  -H "Content-Type: application/json" \
  -d '{"model":"clinical-longformer","text":"Patient presents with chest pain. ECG shows ST elevation. Troponin elevated."}'
```

## Known Issues / Optimization Opportunities

1. **4096-token context**: Longformer uses more memory at 4096 tokens. GPU is justified for this model.

2. **HF_TOKEN plaintext**: Token stored as plaintext env var (intentional per docs).

3. **No PVC storageClassName**: PVC missing storageClassName.

4. **Gateway registration incomplete**: Model not in MODEL_TYPES, MODEL_METADATA, KSERVE_CUSTOM_MODELS, or CONTEXT_WINDOWS in gateway.py.

5. **Longformer global attention**: Server correctly sets global attention on CLS token. This is correct per Longformer architecture.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap + PVC + ISVC spec |
| `kustomization.yaml` | Kustomize resources |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
