# BiomedBERT-large — Model Context

## What This Model Does

BiomedBERT-large by Microsoft. 340M params. Large BERT model pre-trained on PubMed abstracts. State-of-the-art on BioASQ, PubMedQA, and BLURB biomedical benchmarks. Produces 1024-dimensional dense embeddings. Larger variant of BiomedBERT for higher-accuracy biomedical NLP tasks. Max sequence length 512 tokens.

## Source Repo

**HuggingFace**: [microsoft/BiomedNLP-BiomedBERT-large-uncased-abstract](https://huggingface.co/microsoft/BiomedNLP-BiomedBERT-large-uncased-abstract)

Key info from source:
- **Input format**: Biomedical text strings (uncased)
- **Max tokens**: 512
- **License**: MIT
- **Embedding dim**: 1024
- **Backbone**: BERT-large (340M params)

## How The Server Works

- **Pattern**: Custom FastAPI embedding server with HuggingFace Transformers
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`
- **Init container**: Creates venv, installs torch+transformers (CPU), downloads model from HF to PVC
- **ConfigMap**: `biomedbert-large-server` — server code embedded in inferenceservice.yaml
- **PVC**: `biomedbert-large-data` — stores venv + model weights (5Gi)
- **Health**: Custom `/health` endpoint
- **GPU**: 1x shared L40S via time-slicing
- **Env vars**: `MODEL_DIR=/data/model`, `HF_HUB_OFFLINE=1`
- **Pooling**: CLS token
- **Output**: Custom `/v1/science/embed` response format (not OpenAI-compatible)
- **Note**: Uses venv-on-PVC pattern with HF_HUB_OFFLINE=1 for fast restarts

## Gateway Integration

- **k8s ISVC name**: `biomedbert-large`
- **API model ID**: `biomedbert-large` (no mapping in ISVC_NAME_MAP)
- **MODEL_TYPE**: defaults to "chat" — needs update to "embedding"
- **KSERVE_CUSTOM_MODELS**: not listed — needs addition
- **Scale-to-zero**: minReplicas=0, scaleTarget=1, 10m retention

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/biomedbert-large/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=biomedbert-large

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=biomedbert-large -c kserve-container -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/science/embed \
  -H "Content-Type: application/json" \
  -d '{"model":"biomedbert-large","text":"BRCA1 mutations are associated with hereditary breast cancer."}'
```

## Known Issues / Optimization Opportunities

1. **GPU requested but may be excessive**: 340M BERT-large can run on CPU, though slower. GPU is reasonable for this size.

2. **Non-OpenAI API**: Uses `/v1/science/embed` instead of `/v1/embeddings`. Not standard.

3. **Pip dependencies unpinned**: Init container installs deps without version pins.

4. **HF_TOKEN plaintext**: Token stored as plaintext env var in init container (intentional per docs).

5. **Gateway registration incomplete**: Model not in MODEL_TYPES, MODEL_METADATA, KSERVE_CUSTOM_MODELS, or CONTEXT_WINDOWS in gateway.py.

6. **No PVC storageClassName**: PVC missing storageClassName — uses cluster default.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap + PVC + ISVC spec: init container + FastAPI container |
| `kustomization.yaml` | Kustomize resources |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
