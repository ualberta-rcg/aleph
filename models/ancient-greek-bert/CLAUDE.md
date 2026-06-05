# Ancient Greek BERT — Model Context

## What This Model Does

Ancient Greek BERT by pranaydeeps. 110M params. BERT-base model pre-trained on Ancient Greek texts for Digital Humanities and classical studies. Supports masked token prediction and text embeddings for Ancient and Byzantine Greek corpora. Useful for philological analysis, authorship attribution, and textual similarity. Max sequence length 512 tokens.

## Source Repo

**HuggingFace**: [pranaydeeps/Ancient-Greek-BERT](https://huggingface.co/pranaydeeps/Ancient-Greek-BERT)

Key info from source:
- **Input format**: Ancient Greek text (Unicode)
- **Max tokens**: 512
- **License**: MIT
- **Embedding dim**: 768
- **Backbone**: BERT-base (110M params)

## How The Server Works

- **Pattern**: Custom FastAPI embedding server with HuggingFace Transformers
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`
- **Init container**: Creates venv, installs torch+transformers (CPU), downloads model from HF to PVC
- **ConfigMap**: `ancient-greek-bert-server` — server code embedded in inferenceservice.yaml
- **PVC**: `ancient-greek-bert-data` — stores venv + model weights (5Gi)
- **Health**: Custom `/health` endpoint
- **GPU**: 1x shared L40S via time-slicing
- **Env vars**: `MODEL_DIR=/data/model`, `HF_HUB_OFFLINE=1`
- **Pooling**: CLS token
- **Output**: Custom `/v1/science/embed` response format

## Gateway Integration

- **k8s ISVC name**: `ancient-greek-bert`
- **API model ID**: `ancient-greek-bert` (no mapping in ISVC_NAME_MAP)
- **MODEL_TYPE**: defaults to "chat" — needs update to "embedding"
- **KSERVE_CUSTOM_MODELS**: not listed — needs addition
- **Scale-to-zero**: minReplicas=0, scaleTarget=1, 10m retention

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/ancient-greek-bert/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=ancient-greek-bert

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=ancient-greek-bert -c kserve-container -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/science/embed \
  -H "Content-Type: application/json" \
  -d '{"model":"ancient-greek-bert","text":"Ἐν ἀρχῇ ἦν ὁ λόγος"}'
```

## Known Issues / Optimization Opportunities

1. **GPU requested but likely unnecessary**: 110M BERT runs fine on CPU.

2. **Non-OpenAI API**: Uses `/v1/science/embed` instead of `/v1/embeddings`.

3. **HF_TOKEN plaintext**: Token stored as plaintext env var (intentional per docs).

4. **No PVC storageClassName**: PVC missing storageClassName.

5. **Gateway registration incomplete**: Model not in MODEL_TYPES, MODEL_METADATA, KSERVE_CUSTOM_MODELS, or CONTEXT_WINDOWS in gateway.py.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap + PVC + ISVC spec |
| `kustomization.yaml` | Kustomize resources |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
