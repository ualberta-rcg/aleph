# Ancient Greek BERT — Model Context

## What This Model Does

Ancient Greek BERT by pranaydeeps. 110M params (BERT-base) pre-trained on Ancient Greek texts for
Digital Humanities and classical studies. Produces **768-dim [CLS]-pooled embeddings** of
Ancient/Byzantine Greek text (philological analysis, authorship attribution, textual similarity).
Max sequence length 512 tokens.

## Source Repo

**HuggingFace**: [pranaydeeps/Ancient-Greek-BERT](https://huggingface.co/pranaydeeps/Ancient-Greek-BERT)
**License**: MIT

## How The Server Works

- **Pattern**: Custom FastAPI + `transformers` AutoModel, venv-on-PVC.
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`.
- **Init container**: creates venv, installs torch+transformers, downloads model from HF to PVC.
- **ConfigMap**: `ancient-greek-bert-server` (server code embedded in inferenceservice.yaml).
- **PVC**: `ancient-greek-bert-data` — RWX, nfs-models (venv + weights). Migrated RWO→RWX.
- **GPU**: HAMi sub-GPU slice (`gpu: "on"`, `nvidia.com/gpu: 1`).
- **Env**: `MODEL_DIR=/data/model`, `HF_HUB_OFFLINE=1`.
- **Pooling**: [CLS] token.

## API

- **Primary**: `POST /v1/embeddings` (OpenAI-compliant; batch + usage) — added 2026-06-19.
- **Secondary**: `POST /v1/science/embed` (domain endpoint, kept for back-compat).
- **Health**: `GET /health`.

## Gateway Integration

- **k8s ISVC name**: `ancient-greek-bert`
- **API model ID**: `ancient-greek-bert`
- **type**: `embedding` (details.yaml schema v2)
- **Scale-to-zero**: minReplicas=0, 10m retention.

## Deploy / Update / Test

```bash
kubectl apply -f models/ancient-greek-bert/pvc.yaml
kubectl apply -f models/ancient-greek-bert/inferenceservice.yaml
kubectl apply -f models/ancient-greek-bert/details.yaml

# Status / logs
kubectl get pods -n models -l serving.kserve.io/inferenceservice=ancient-greek-bert
kubectl logs -n models -l serving.kserve.io/inferenceservice=ancient-greek-bert -c kserve-container -f

# Test (external via gateway VIP + Tyk auth)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/ancient-greek-bert/test.py
# Or inside the gateway pod (no auth):
cat models/ancient-greek-bert/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

## Known Issues / Gotchas

1. **GPU likely unnecessary**: 110M BERT runs fine on CPU; GPU slice is conservative.
2. **Dual endpoint**: `/v1/embeddings` is primary; `/v1/science/embed` kept for back-compat — keep both in sync if the server changes.
3. Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** (dim 768, batch, model-echo, usage, distinctness, encoding_format, truncation, guardrails, catalog).

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | Model card (schema v2, type: embedding) |
| `inferenceservice.yaml` | ConfigMap (server.py) + ISVC spec |
| `pvc.yaml` | PVC `ancient-greek-bert-data` (RWX, nfs-models) |
| `test.py` | Gateway test battery (10 checks) |
| `README.md` | Model overview |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
