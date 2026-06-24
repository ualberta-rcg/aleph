# Clinical-Longformer — Model Context

## What This Model Does

Clinical-Longformer by yikuan8. 149M params. Longformer model pre-trained on MIMIC-III clinical notes. Handles long clinical documents up to 4096 tokens, far exceeding standard 512-token BERT models. Superior to ClinicalBERT for long clinical texts like discharge summaries and radiology reports. Apache 2.0 license.

## Source Repo

**HuggingFace**: [yikuan8/Clinical-Longformer](https://huggingface.co/yikuan8/Clinical-Longformer)

Key info from source:
- **Input format**: Clinical text strings
- **Max tokens**: 4096 (Longformer sliding window attention)
- **License**: Apache-2.0
- **Embedding dim**: 768
- **Training data**: MIMIC-III clinical notes

## How The Server Works

- **Pattern**: Custom FastAPI + `transformers` LongformerModel, venv-on-PVC.
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`.
- **Init container**: creates venv, installs torch+transformers, downloads model to PVC.
- **ConfigMap**: `clinical-longformer-server` (server code embedded in inferenceservice.yaml).
- **PVC**: `clinical-longformer-data` — RWX, nfs-models (venv + weights; migrated RWO→RWX).
- **GPU**: HAMi slice (`gpu: "on"`, `nvidia.com/gpumem: 10240`).
- **Env**: `MODEL_DIR=/data/model`, `HF_HUB_OFFLINE=1`.
- **Pooling**: [CLS] token with global attention (Longformer-specific) → 768-dim.

## API

- **Primary**: `POST /v1/embeddings` (OpenAI-compliant) — added 2026-06-19.
- **Secondary**: `POST /v1/science/embed` (domain endpoint, kept for back-compat).
- **Health**: `GET /health`.

## Gateway Integration

- **k8s ISVC name**: `clinical-longformer`
- **API model ID**: `clinical-longformer`
- **type**: `embedding`, context_window 4096 (details.yaml schema v2)
- **Scale-to-zero**: minReplicas=0, 10m retention.

## Deploy / Update / Test

```bash
kubectl apply -f models/clinical-longformer/pvc.yaml
kubectl apply -f models/clinical-longformer/inferenceservice.yaml
kubectl apply -f models/clinical-longformer/details.yaml

# Status / logs
kubectl get pods -n models -l serving.kserve.io/inferenceservice=clinical-longformer
kubectl logs -n models -l serving.kserve.io/inferenceservice=clinical-longformer -c kserve-container -f

# Test (external via gateway VIP + Tyk auth)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/clinical-longformer/test.py
# Or inside the gateway pod (no auth):
cat models/clinical-longformer/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

## Known Issues / Gotchas

1. **Longformer global attention on CLS**: the server sets a global-attention mask on the CLS
   token (required by Longformer for a meaningful pooled embedding). Do not remove it.
2. **4096-token context**: more memory at full context; the 10 GiB GPU slice covers it. On CPU,
   inference is slow (~2 min) — the model is on a GPU slice for this reason.
3. **Dual endpoint**: `/v1/embeddings` primary; `/v1/science/embed` kept — keep in sync.
4. Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL**.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | Model card (schema v2, type: embedding) |
| `inferenceservice.yaml` | ConfigMap (server.py) + ISVC spec |
| `pvc.yaml` | PVC `clinical-longformer-data` (RWX, nfs-models) |
| `test.py` | Gateway test battery (10 checks) |
| `README.md` | Model overview |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
