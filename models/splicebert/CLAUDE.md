# SpliceBERT — Model Context

## What This Model Does

SpliceBERT by Zhihan Zhou et al. 86M params. BERT-based model pre-trained on 2 million RNA sequences across multiple species for splice site prediction and RNA analysis. Stored under the HF repo `zhihan1996/DNA_bert_6` which uses 6-mer tokenization. Produces 768-dimensional embeddings for RNA splicing analysis, alternative splicing prediction, and transcriptomics. Max sequence length 510 tokens.

## Source Repo

**HuggingFace**: [zhihan1996/DNA_bert_6](https://huggingface.co/zhihan1996/DNA_bert_6)
**Paper**: [SpliceBERT: a pre-trained deep learning model for RNA splicing prediction](https://arxiv.org/abs/2305.15805)

Key info from source:
- **Tokenizer**: 6-mer tokenization (DNA_bert_6)
- **Max tokens**: 510 (not the usual 512 — 6-mer tokenization uses 2 special tokens)
- **License**: Apache-2.0
- **Embedding dim**: 768
- **trust_remote_code**: Required
- **Training data**: 2M RNA sequences from multiple species

## How The Server Works

- **Pattern**: Custom FastAPI embedding server with HuggingFace Transformers
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`
- **Init container**: Creates venv, installs torch+transformers (CPU), downloads model from HF
- **ConfigMap**: `splicebert-server` — server code embedded in inferenceservice.yaml
- **PVC**: `splicebert-data` — stores venv + model weights (5Gi, NFS ReadWriteMany)
- **Health**: Custom `/health` endpoint
- **CPU only**: No GPU allocation. PyTorch CPU with float32.
- **Env vars**: `MODEL_DIR=/data/model`, `MODEL_NAME=splicebert-86m`
- **Pooling**: Mean pooling with attention mask
- **Output**: OpenAI-compatible `/v1/embeddings` response format

## Gateway Integration

- **k8s ISVC name**: `splicebert`
- **API model ID**: `splicebert-86m` (mapped via ISVC_NAME_MAP)
- **MODEL_TYPE**: embedding
- **KSERVE_CUSTOM_MODELS**: yes — uses `/v1/` prefix
- **CONTEXT_WINDOWS**: 510
- **Scale-to-zero**: minReplicas=0, scaleTarget=2, 900s retention

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/splicebert/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=splicebert

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=splicebert -c kserve-container -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"splicebert-86m","input":"AUGCUAGCUAGCUAAGCUAGCUAAGC"}'
```

## Known Issues / Optimization Opportunities

1. **CPU only**: Model runs on CPU with PyTorch. Could use ONNX export for faster inference.

2. **Pip dependencies unpinned**: Init container installs deps without version pins.

3. **MAX_LEN is 510, not 512**: Correct for 6-mer tokenization (2 special tokens), but this is hardcoded in server code rather than set via env var. Falls back from env with default 510.

4. **trust_remote_code required**: Model uses custom tokenizer/model code from the HF repo.

5. **Token count uses char count**: Usage reports `prompt_tokens` as character count (`sum(len(s))`), appropriate for nucleotide sequences.

6. **HF_TOKEN plaintext**: Token stored as plaintext env var in init container (intentional per docs).

7. **Repo naming confusion**: HF repo is `DNA_bert_6` but the model is called SpliceBERT in papers. The k8s name `splicebert` maps to this repo.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap + ISVC spec: init container + FastAPI container |
| `kustomization.yaml` | Kustomize resources |
| `pvc.yaml` | Dedicated PVC (splicebert-data) |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
