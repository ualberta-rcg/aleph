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

- **Pattern**: Custom FastAPI + `transformers` AutoModel, venv-on-PVC.
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`.
- **Init container**: creates venv, installs torch+transformers, downloads model to PVC.
- **ConfigMap**: `biomed-roberta-server` (server code embedded in inferenceservice.yaml).
- **PVC**: `biomed-roberta` — RWX, nfs-models (venv + weights; bare fleet naming, was `biomed-roberta-data`/`model-data`).
- **GPU**: HAMi slice (`gpu: "on"`, `nvidia.com/gpumem: 8192`), fp16.
- **Env**: `HF_HOME=/data/hf_cache`.
- **Pooling**: mean pooling with attention mask → 768-dim.

## API

- **Primary**: `POST /v1/embeddings` (OpenAI-compliant; batch + usage).
- **Health**: `GET /health`.

## Gateway Integration

- **k8s ISVC name**: `biomed-roberta`
- **API model ID**: `biomed-roberta`
- **type**: `embedding` (details.yaml schema v2)
- **Always-on**: minReplicas=1 (max 3, scaleTarget 8), 15m retention.

## Deploy / Update / Test

```bash
kubectl apply -f models/biomed-roberta/pvc.yaml
kubectl apply -f models/biomed-roberta/inferenceservice.yaml
kubectl apply -f models/biomed-roberta/details.yaml

# Status / logs
kubectl get pods -n models -l serving.kserve.io/inferenceservice=biomed-roberta
kubectl logs -n models -l serving.kserve.io/inferenceservice=biomed-roberta -c kserve-container -f

# Test (external via gateway VIP + Tyk auth)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/biomed-roberta/test.py
# Or inside the gateway pod (no auth):
cat models/biomed-roberta/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

## Known Issues / Gotchas

1. **GPU likely unnecessary**: 125M RoBERTa runs fine on CPU; GPU slice is conservative.
2. Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** (dim 768, batch, model-echo, usage, distinctness, encoding_format, truncation, guardrails, catalog).

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | Model card (schema v2, type: embedding) |
| `inferenceservice.yaml` | ConfigMap (server.py) + ISVC spec |
| `pvc.yaml` | PVC `biomed-roberta` (RWX, nfs-models) |
| `test.py` | Gateway test battery (10 checks) |
| `README.md` | Model overview |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
