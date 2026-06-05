# BioMed-RoBERTa — Model Context

## What This Model Does

BioMed-RoBERTa by Allen AI. 110M params. RoBERTa-base model pre-trained on biomedical text (PubMed abstracts + PMC full text). Produces 768-dimensional dense embeddings for biomedical NLP tasks including NER, relation extraction, and document classification. Max sequence length 512 tokens.

## Source Repo

**HuggingFace**: [allenai/biomed_roberta_base](https://huggingface.co/allenai/biomed_roberta_base)

Key info from source:
- **Input format**: Biomedical text strings
- **Max tokens**: 512
- **License**: Apache-2.0
- **Embedding dim**: 768
- **Backbone**: RoBERTa-base (110M params)

## How The Server Works

- **Pattern**: Custom FastAPI embedding server with HuggingFace Transformers
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`
- **Init container**: Creates venv, installs torch+transformers (CUDA), downloads model from HF
- **ConfigMap**: `biomed-roberta-server` — server code embedded in inferenceservice.yaml
- **PVC**: `biomed-roberta-data` — stores venv + model weights (3Gi, NFS)
- **Health**: Custom `/health` endpoint
- **GPU**: 1x shared L40S via time-slicing, float16 on GPU / float32 on CPU
- **Env vars**: `HF_HOME=/data/hf_cache`
- **Pooling**: Mean pooling with attention mask
- **Output**: OpenAI-compatible `/v1/embeddings` response format
- **Note**: Downloads model at runtime via `AutoModel.from_pretrained(MODEL_ID)` each startup (no local_dir caching)

## Gateway Integration

- **k8s ISVC name**: `biomed-roberta`
- **API model ID**: `biomed-roberta` (no mapping in ISVC_NAME_MAP)
- **MODEL_TYPE**: defaults to "chat" — needs update to "embedding"
- **KSERVE_CUSTOM_MODELS**: not listed — needs addition
- **Scale-to-zero**: minReplicas=0, scaleTarget=5, 900s retention

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/biomed-roberta/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=biomed-roberta

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=biomed-roberta -c kserve-container -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"biomed-roberta","input":"EGFR mutations predict response to tyrosine kinase inhibitors in NSCLC."}'
```

## Known Issues / Optimization Opportunities

1. **Model re-downloaded each restart**: Uses `AutoModel.from_pretrained(MODEL_ID)` at runtime, not cached to PVC via snapshot_download. Should use venv+PVC pattern.

2. **GPU requested but likely unnecessary**: 110M RoBERTa runs fine on CPU.

3. **Pip dependencies unpinned**: Init container installs deps without version pins.

4. **Gateway registration incomplete**: Model not in MODEL_TYPES, MODEL_METADATA, KSERVE_CUSTOM_MODELS, or CONTEXT_WINDOWS in gateway.py.

5. **PVC read-only mount**: Container mounts PVC read-only but model loading writes to HF cache on PVC.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap + PVC + ISVC spec: init container + FastAPI container |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
