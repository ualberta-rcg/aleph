# MedCPT Query Encoder — Model Context

## What This Model Does

MedCPT Query Encoder by NCBI. 110M params. BERT-base model fine-tuned for medical query embeddings using contrastive pre-training on PubMed click logs. Produces CLS token embeddings for biomedical query encoding. Designed to pair with MedCPT Article Encoder for retrieval-augmented generation. Short-context model (max 64 tokens for queries).

## Source Repo

**HuggingFace**: [ncbi/MedCPT-Query-Encoder](https://huggingface.co/ncbi/MedCPT-Query-Encoder)
**Paper**: [MedCPT: Contrastive Pre-trained Transformers for Zero-shot Medical Information Retrieval](https://arxiv.org/abs/2307.00589)

Key info from source:
- **Input format**: Short medical search queries
- **Max tokens**: 64 (optimized for queries, not documents)
- **License**: MIT
- **Embedding dim**: 768
- **Pairs with**: MedCPT Article Encoder for dual-encoder retrieval

## How The Server Works

- **Pattern**: Custom FastAPI embedding server with HuggingFace Transformers
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`
- **Init container**: Creates venv, installs torch+transformers (CUDA), downloads model from HF
- **ConfigMap**: `medcpt-query-server` — server code embedded in inferenceservice.yaml
- **PVC**: `medcpt-query-data` — stores venv + model weights (3Gi, NFS)
- **Health**: Custom `/health` endpoint
- **GPU**: 1x shared L40S via time-slicing, float16 on GPU / float32 on CPU
- **Env vars**: `HF_HOME=/data/hf_cache`
- **Pooling**: CLS token
- **Output**: OpenAI-compatible `/v1/embeddings` response format
- **Note**: Downloads model at runtime via `from_pretrained(MODEL_ID)` each startup (no local_dir caching)

## Gateway Integration

- **k8s ISVC name**: `medcpt-query`
- **API model ID**: `medcpt-query` (no mapping in ISVC_NAME_MAP)
- **MODEL_TYPE**: defaults to "chat" — needs update to "embedding"
- **KSERVE_CUSTOM_MODELS**: not listed — needs addition
- **Scale-to-zero**: minReplicas=0, scaleTarget=5, 900s retention

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/medcpt-query/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=medcpt-query

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=medcpt-query -c kserve-container -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"medcpt-query","input":"What are the side effects of metformin?"}'
```

## Known Issues / Optimization Opportunities

1. **Model re-downloaded each restart**: Uses `from_pretrained(MODEL_ID)` at runtime, not cached to PVC via snapshot_download.

2. **GPU requested but likely unnecessary**: 110M BERT runs fine on CPU. Queries are short (64 tokens).

3. **Pip dependencies unpinned**: Init container installs deps without version pins.

4. **Gateway registration incomplete**: Model not in MODEL_TYPES, MODEL_METADATA, KSERVE_CUSTOM_MODELS, or CONTEXT_WINDOWS in gateway.py.

5. **PVC read-only mount**: Container mounts PVC read-only but model loading writes to HF cache on PVC.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap + PVC + ISVC spec |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
