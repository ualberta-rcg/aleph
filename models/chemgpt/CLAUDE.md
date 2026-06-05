# ChemGPT-1.2B — Model Context

## What This Model Does

ChemGPT-1.2B by ncfrey. 1.2B params. GPT-Neo model trained on PubChem SMILES for autoregressive molecule generation and completion. Generates valid drug-like molecules as SMILES strings. Also provides molecular embeddings via hidden state extraction. Ideal for de novo drug design and high-throughput molecular screening. Max sequence length 512 tokens.

## Source Repo

**HuggingFace**: [ncfrey/ChemGPT-1.2B](https://huggingface.co/ncfrey/ChemGPT-1.2B)

Key info from source:
- **Input format**: SMILES string prompt
- **Max tokens**: 512
- **License**: MIT
- **Architecture**: GPT-Neo (1.2B params)
- **Training data**: PubChem SMILES

## How The Server Works

- **Pattern**: Custom FastAPI generation server with HuggingFace Transformers
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`
- **Init container**: Creates venv, installs torch+transformers (CPU), downloads model from HF to PVC
- **ConfigMap**: `chemgpt-server` — server code embedded in inferenceservice.yaml
- **PVC**: `chemgpt-data` — stores venv + model weights (10Gi)
- **Health**: Custom `/health` endpoint
- **GPU**: 1x shared L40S via time-slicing, float16 on GPU / float32 on CPU
- **Env vars**: `MODEL_DIR=/data/model`, `HF_HUB_OFFLINE=1`
- **Output**: Custom `/v1/science/generate` and `/v1/science/embed` response formats
- **Note**: Uses venv-on-PVC pattern with HF_HUB_OFFLINE=1 for fast restarts

## Gateway Integration

- **k8s ISVC name**: `chemgpt`
- **API model ID**: `chemgpt-1.2b` (no mapping in ISVC_NAME_MAP)
- **MODEL_TYPE**: defaults to "chat" — needs update to "generate"
- **KSERVE_CUSTOM_MODELS**: not listed — needs addition
- **Scale-to-zero**: minReplicas=0, scaleTarget=1, 10m retention

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/chemgpt/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=chemgpt

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=chemgpt -c kserve-container -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/science/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"chemgpt-1.2b","smiles":"CC(=O)","max_new_tokens":50,"num_return_sequences":3}'
```

## Known Issues / Optimization Opportunities

1. **GPU requested but may be unnecessary for embeddings**: 1.2B GPT-Neo benefits from GPU for generation but CPU works.

2. **No SMILES validation**: Server does not validate input SMILES strings.

3. **HF_TOKEN plaintext**: Token stored as plaintext env var in init container (intentional per docs).

4. **Duplicate retention annotation**: Has both `scale-to-zero-pod-retention-period` and `scaleToZeroPodRetentionPeriod` (camelCase).

5. **Gateway registration incomplete**: Model not in MODEL_TYPES, MODEL_METADATA, KSERVE_CUSTOM_MODELS, or CONTEXT_WINDOWS in gateway.py.

6. **No PVC storageClassName**: PVC missing storageClassName.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap + PVC + ISVC spec |
| `kustomization.yaml` | Kustomize resources |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
