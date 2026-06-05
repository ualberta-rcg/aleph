# BioGPT — Model Context

## What This Model Does

BioGPT by Microsoft. 347M params. GPT-2 style autoregressive language model pre-trained on 15M PubMed abstracts. Generates biomedical text, descriptions of drugs/proteins/diseases, and can perform relation extraction. Max input length 1024 tokens.

## Source Repo

**HuggingFace**: [microsoft/biogpt](https://huggingface.co/microsoft/biogpt)
**Paper**: [BioGPT: generative pre-trained transformer for biomedical text generation and mining](https://arxiv.org/abs/2210.12641)

Key info from source:
- **Input format**: Text prompt (biomedical context)
- **Max tokens**: 1024
- **License**: MIT
- **Architecture**: GPT-2 style (347M params)
- **Training data**: 15M PubMed abstracts

## How The Server Works

- **Pattern**: Custom FastAPI text generation server with HuggingFace Transformers
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`
- **Init container**: Creates venv, installs torch+transformers+sacremoses (CUDA), downloads model from HF
- **ConfigMap**: `biogpt-server` — server code embedded in inferenceservice.yaml
- **PVC**: `biogpt-data` — stores venv + model weights (5Gi, NFS)
- **Health**: Custom `/health` endpoint
- **GPU**: 1x shared L40S via time-slicing, float16 on GPU / float32 on CPU
- **Env vars**: `HF_HOME=/data/hf_cache`
- **Output**: OpenAI-compatible `/v1/completions` response format
- **Note**: Downloads model at runtime via `from_pretrained(MODEL_ID)` each startup (no local_dir caching)

## Gateway Integration

- **k8s ISVC name**: `biogpt`
- **API model ID**: `biogpt` (no mapping in ISVC_NAME_MAP)
- **MODEL_TYPE**: defaults to "chat" — needs update to "generate"
- **KSERVE_CUSTOM_MODELS**: not listed — needs addition
- **Scale-to-zero**: minReplicas=0, scaleTarget=5, 900s retention

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/biogpt/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=biogpt

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=biogpt -c kserve-container -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"biogpt","prompt":"The role of p53 in","max_tokens":50}'
```

## Known Issues / Optimization Opportunities

1. **Model re-downloaded each restart**: Uses `from_pretrained(MODEL_ID)` at runtime, not cached to PVC via snapshot_download.

2. **GPU requested but may be unnecessary**: 347M GPT runs on CPU with acceptable latency.

3. **Pip dependencies unpinned**: Init container installs deps without version pins.

4. **Gateway registration incomplete**: Model not in MODEL_TYPES, MODEL_METADATA, KSERVE_CUSTOM_MODELS, or CONTEXT_WINDOWS in gateway.py.

5. **No max_tokens cap**: Server accepts arbitrary max_tokens without upper limit.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap + PVC + ISVC spec: init container + FastAPI container |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
