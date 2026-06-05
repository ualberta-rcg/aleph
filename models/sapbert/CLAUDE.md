# SapBERT — Model Context

## What This Model Does

SapBERT by Cambridge LTL. 110M params. Self-alignment pre-trained BERT for biomedical entity linking. Maps biomedical entity mentions (drug names, disease names, gene symbols) to UMLS concept embeddings. Trained on UMLS knowledge graph for named entity normalization, medical concept retrieval, and clinical NLP. Uses CLS token with short context (max 25 tokens).

## Source Repo

**HuggingFace**: [cambridgeltl/SapBERT-from-PubMedBERT-fulltext](https://huggingface.co/cambridgeltl/SapBERT-from-PubMedBERT-fulltext)
**Paper**: [SapBERT: Self-alignment Pre-training for Biomedical Entity Representations](https://arxiv.org/abs/2010.11784)

Key info from source:
- **Input format**: Short entity mentions (drug names, disease names)
- **Max tokens**: 25 (entity-focused, not document-level)
- **License**: MIT
- **Embedding dim**: 768
- **Backbone**: PubMedBERT (110M params)

## How The Server Works

- **Pattern**: Custom FastAPI embedding server with HuggingFace Transformers
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`
- **Init container**: Creates venv, installs torch+transformers (CPU), downloads model from HF to PVC
- **ConfigMap**: `sapbert-server` — server code embedded in inferenceservice.yaml
- **PVC**: `sapbert-data` — stores venv + model weights (5Gi)
- **Health**: Custom `/health` endpoint
- **GPU**: 1x shared L40S via time-slicing
- **Env vars**: `MODEL_DIR=/data/model`, `HF_HUB_OFFLINE=1`
- **Pooling**: CLS token (as per SapBERT paper)
- **Output**: Custom `/v1/science/embed` response format

## Gateway Integration

- **k8s ISVC name**: `sapbert`
- **API model ID**: `sapbert` (no mapping in ISVC_NAME_MAP)
- **MODEL_TYPE**: defaults to "chat" — needs update to "embedding"
- **KSERVE_CUSTOM_MODELS**: not listed — needs addition
- **Scale-to-zero**: minReplicas=0, scaleTarget=1, 10m retention

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/sapbert/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=sapbert

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=sapbert -c kserve-container -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/science/embed \
  -H "Content-Type: application/json" \
  -d '{"model":"sapbert","text":"myocardial infarction"}'
```

## Known Issues / Optimization Opportunities

1. **GPU requested but likely unnecessary**: 110M BERT with max 25 tokens runs very fast on CPU.

2. **Non-OpenAI API**: Uses `/v1/science/embed` instead of `/v1/embeddings`.

3. **HF_TOKEN plaintext**: Token stored as plaintext env var (intentional per docs).

4. **No PVC storageClassName**: PVC missing storageClassName.

5. **Gateway registration incomplete**: Model not in MODEL_TYPES, MODEL_METADATA, KSERVE_CUSTOM_MODELS, or CONTEXT_WINDOWS in gateway.py.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap + PVC + ISVC spec |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
