# Zoobot (ConvNeXt-Nano) — Model Context

## What This Model Does

Zoobot galaxy morphology encoder by M. Walmsley. 15M params. ConvNeXt-Nano backbone pre-trained on Galaxy Zoo volunteer classifications from millions of galaxies. Produces 640-dimensional embeddings for galaxy morphology classification, clustering, and similarity search. Uses the `timm` library with HuggingFace Hub weights. CPU inference via PyTorch. Not an ONNX model — uses timm directly.

## Source Repo

**HuggingFace**: [mwalmsley/zoobot-encoder-convnext_nano](https://huggingface.co/mwalmsley/zoobot-encoder-convnext_nano)
**Paper**: [Galaxy Zoo DECaLS: Detailed morphology classification](https://arxiv.org/abs/2202.13048)

Key info from source:
- **Input size**: 224x224 pixels (galaxy images)
- **License**: Apache-2.0
- **Embedding dim**: 640
- **Backbone**: ConvNeXt-Nano (from timm)
- **Training data**: Galaxy Zoo volunteer labels on DECaLS galaxies

## How The Server Works

- **Pattern**: Custom FastAPI with PyTorch/timm inference (NOT ONNX)
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`
- **Init container**: Creates venv, installs timm+torch (CPU wheels). Model weights downloaded at runtime by timm from HF Hub.
- **ConfigMap**: `zoobot-server` — server code embedded in inferenceservice.yaml
- **PVC**: `zoobot-data` — stores venv + HF Hub cache + torch cache (5Gi, NFS ReadWriteMany)
- **Health**: Custom `/health` endpoint
- **CPU only**: No GPU allocation. PyTorch CPU inference.
- **Env vars**: `MODEL_NAME=zoobot-15m`, `HF_HOME=/data/hf-hub`, `TORCH_HOME=/data/torch`
- **Note**: PVC is mounted read-write (not readOnly) because model weights are downloaded at runtime to `/data/hf-hub`

## Gateway Integration

- **k8s ISVC name**: `zoobot`
- **API model ID**: `zoobot-15m` (mapped via ISVC_NAME_MAP)
- **MODEL_TYPE**: classify
- **KSERVE_CUSTOM_MODELS**: yes — uses `/v1/` prefix
- **Scale-to-zero**: minReplicas=0, scaleTarget=2, 900s retention

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/zoobot/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=zoobot

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=zoobot -c kserve-container -f

# Test (public) — need a base64-encoded galaxy image
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/vision/embed \
  -H "Content-Type: application/json" \
  -d '{"model":"zoobot-15m","image":"<base64_encoded_jpeg>"}'
```

## Known Issues / Optimization Opportunities

1. **CPU only**: Model runs on CPU with PyTorch. Could use GPU for faster batch inference.

2. **No ONNX**: Uses PyTorch/timm directly. Could export to ONNX for faster CPU inference.

3. **Runtime model download**: Weights are not downloaded in init container — timm downloads them on first load. First request after cold start will be slow. Could pre-download in init container.

4. **PVC mounted read-write**: Unlike other models, the PVC is not mounted readOnly because weights are downloaded at runtime. This could cause issues if multiple pods write simultaneously.

5. **Pip dependencies unpinned**: Init container installs deps without version pins.

6. **Only exposes /embed endpoint**: Despite gateway listing both `/v1/vision/classify` and `/v1/vision/embed`, the server only implements `/v1/vision/embed`. Classification endpoint is missing.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap + ISVC spec: init container + FastAPI container |
| `kustomization.yaml` | Kustomize resources |
| `pvc.yaml` | Dedicated PVC (zoobot-data) |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
