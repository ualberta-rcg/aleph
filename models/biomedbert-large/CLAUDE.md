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

- **Pattern**: Custom FastAPI + `transformers` AutoModel, venv-on-PVC.
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`.
- **Init container**: creates venv, installs torch+transformers, downloads model to PVC.
- **ConfigMap**: `biomedbert-large-server` (server code embedded in inferenceservice.yaml).
- **PVC**: `biomedbert-large-data` — RWX, nfs-models (venv + weights; migrated RWO→RWX).
- **GPU**: HAMi slice (`gpu: "on"`, `nvidia.com/gpumem: 10240`).
- **Env**: `MODEL_DIR=/data/model`, `HF_HUB_OFFLINE=1`.
- **Pooling**: [CLS] token → 1024-dim.

## API

- **Primary**: `POST /v1/embeddings` (OpenAI-compliant; batch + usage) — added 2026-06-19.
- **Secondary**: `POST /v1/science/embed` (domain endpoint, kept for back-compat).
- **Health**: `GET /health`.

## Gateway Integration

- **k8s ISVC name**: `biomedbert-large`
- **API model ID**: `biomedbert-large`
- **type**: `embedding` (details.yaml schema v2)
- **Scale-to-zero**: minReplicas=0, 10m retention.

## Deploy / Update / Test

```bash
kubectl apply -f models/biomedbert-large/pvc.yaml
kubectl apply -f models/biomedbert-large/inferenceservice.yaml
kubectl apply -f models/biomedbert-large/details.yaml

# Status / logs
kubectl get pods -n models -l serving.kserve.io/inferenceservice=biomedbert-large
kubectl logs -n models -l serving.kserve.io/inferenceservice=biomedbert-large -c kserve-container -f

# Test (external via gateway VIP + Tyk auth)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/biomedbert-large/test.py
# Or inside the gateway pod (no auth):
cat models/biomedbert-large/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

## Known Issues / Gotchas

1. **Dual endpoint**: `/v1/embeddings` is primary; `/v1/science/embed` kept for back-compat — keep both in sync if the server changes.
2. **GPU sized for headroom**: 340M BERT-large fits a 10 GiB slice; CPU works but is slower.
3. Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** (dim 1024, batch, model-echo, usage, distinctness, encoding_format, truncation, guardrails, catalog).

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | Model card (schema v2, type: embedding) |
| `inferenceservice.yaml` | ConfigMap (server.py) + ISVC spec |
| `pvc.yaml` | PVC `biomedbert-large-data` (RWX, nfs-models) |
| `test.py` | Gateway test battery (10 checks) |
| `README.md` | Model overview |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
