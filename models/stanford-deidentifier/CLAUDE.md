# Stanford Deidentifier — Model Context

## What This Model Does

Stanford Deidentifier by Stanford AIMI. 110M params. BERT-base token classification model for removing Protected Health Information (PHI) from clinical notes. Detects names, dates, IDs, locations, and other HIPAA identifiers. Critical for HIPAA-compliant clinical NLP pipelines. 1.46M HuggingFace downloads. Max sequence length 512 tokens.

## Source Repo

**HuggingFace**: [StanfordAIMI/stanford-deidentifier-base](https://huggingface.co/StanfordAIMI/stanford-deidentifier-base)

Key info from source:
- **Input format**: Clinical note text
- **Max tokens**: 512
- **License**: Apache-2.0
- **Backbone**: BERT-base (110M params), token classification head
- **PHI types detected**: Names, dates, IDs, locations, phone, age, etc.

## How The Server Works

- **Pattern**: Custom FastAPI NER server with HuggingFace Transformers pipeline
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`
- **Init container**: Creates venv, installs torch+transformers (CPU), downloads model from HF to PVC
- **ConfigMap**: `stanford-deidentifier-server` — server code embedded in inferenceservice.yaml
- **PVC**: `stanford-deidentifier-data` — stores venv + model weights (5Gi)
- **Health**: Custom `/health` endpoint
- **GPU**: 1x shared L40S via time-slicing
- **Env vars**: `MODEL_DIR=/data/model`, `HF_HUB_OFFLINE=1`
- **Output**: Custom `/v1/science/deidentify` (entities + anonymized text) and `/v1/science/embed` response formats

## Gateway Integration

- **k8s ISVC name**: `stanford-deidentifier`
- **API model ID**: `stanford-deidentifier` (no mapping in ISVC_NAME_MAP)
- **MODEL_TYPE**: defaults to "chat" — needs update to "deidentify"
- **KSERVE_CUSTOM_MODELS**: not listed — needs addition
- **Scale-to-zero**: minReplicas=0, scaleTarget=1, 10m retention

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/stanford-deidentifier/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=stanford-deidentifier

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=stanford-deidentifier -c kserve-container -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/science/deidentify \
  -H "Content-Type: application/json" \
  -d '{"model":"stanford-deidentifier","text":"Patient John Smith visited on 2024-01-15 for chest pain at Stanford Hospital."}'
```

## Known Issues / Optimization Opportunities

1. **GPU requested but likely unnecessary**: 110M BERT NER runs fine on CPU.

2. **Pipeline created per request**: Uses `pipeline("token-classification", ...)` inside the request handler. Should be cached globally.

3. **HF_TOKEN plaintext**: Token stored as plaintext env var (intentional per docs).

4. **No PVC storageClassName**: PVC missing storageClassName.

5. **Gateway registration incomplete**: Model not in MODEL_TYPES, MODEL_METADATA, KSERVE_CUSTOM_MODELS, or CONTEXT_WINDOWS in gateway.py.

6. **Anonymization is naive**: Replaces entities right-to-left by character offset. May break with overlapping entities or multi-byte characters.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap + PVC + ISVC spec |
| `kustomization.yaml` | Kustomize resources |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
