# BioLinkBERT — Model Context

## What This Model Does

BioLinkBERT by Stanford. 110M params. BERT-base model leveraging document link structure (citation links, hyperlinks) for enhanced biomedical text understanding. Produces 768-dimensional dense embeddings that capture inter-document relationships. Outperforms BioBERT on biomedical NER and relation extraction benchmarks. Max sequence length 512 tokens.

## Source Repo

**HuggingFace**: [michiyasunaga/BioLinkBERT-base](https://huggingface.co/michiyasunaga/BioLinkBERT-base)
**Paper**: [LinkBERT: Pretraining Language Models with Document Links](https://arxiv.org/abs/2203.15827)

Key info from source:
- **Input format**: Biomedical text strings
- **Max tokens**: 512
- **License**: MIT
- **Embedding dim**: 768
- **Backbone**: BERT-base (110M params)

## How The Server Works

- **Pattern**: Custom FastAPI + `transformers` AutoModel, venv-on-PVC.
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`.
- **Init container**: creates venv, installs torch+transformers (CUDA), downloads model to PVC.
- **ConfigMap**: `biolinkbert-server` (server code embedded in inferenceservice.yaml).
- **PVC**: `biolinkbert-data` — RWX, nfs-models (venv + weights; migrated RWO→RWX).
- **GPU**: HAMi slice (`gpu: "on"`, `nvidia.com/gpumem: 8192`), fp16.
- **Env**: `HF_HOME=/data/hf_cache`.
- **Pooling**: mean pooling with attention mask.

## API

- **Primary**: `POST /v1/embeddings` (OpenAI-compliant; batch + usage) — 768-dim.
- **Health**: `GET /health`.

## Gateway Integration

- **k8s ISVC name**: `biolinkbert`
- **API model ID**: `biolinkbert`
- **type**: `embedding` (details.yaml schema v2)
- **Scale-to-zero**: minReplicas=0, 15m retention.

## Deploy / Update / Test

```bash
kubectl apply -f models/biolinkbert/pvc.yaml
kubectl apply -f models/biolinkbert/inferenceservice.yaml
kubectl apply -f models/biolinkbert/details.yaml

# Status / logs
kubectl get pods -n models -l serving.kserve.io/inferenceservice=biolinkbert
kubectl logs -n models -l serving.kserve.io/inferenceservice=biolinkbert -c kserve-container -f

# Test (external via gateway VIP + Tyk auth)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/biolinkbert/test.py
# Or inside the gateway pod (no auth):
cat models/biolinkbert/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

## Known Issues / Gotchas

1. **GPU likely unnecessary**: 110M BERT runs fine on CPU; GPU slice is conservative.
2. **Cold-start 404**: gateway can return 404 briefly during scale-from-zero (pre-warm before testing).
3. Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** (dim 768, batch, model-echo, usage, distinctness, encoding_format, truncation, guardrails, catalog).

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | Model card (schema v2, type: embedding) |
| `inferenceservice.yaml` | ConfigMap (server.py) + ISVC spec |
| `pvc.yaml` | PVC `biolinkbert-data` (RWX, nfs-models) |
| `test.py` | Gateway test battery (10 checks) |
| `README.md` | Model overview |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
