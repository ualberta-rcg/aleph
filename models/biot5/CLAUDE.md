# BioT5 — Model Context

## What This Model Does

BioT5 by QizhiPei. 300M params. T5-base model for cross-modal biology and chemistry tasks. Uses SELFIES molecular representation for 100% valid molecule generation. Supports molecule captioning (mol2text), text-conditioned molecule generation (text2mol), and drug-target interaction prediction. Max sequence length 512 tokens.

## Source Repo

**HuggingFace**: [QizhiPei/biot5-base](https://huggingface.co/QizhiPei/biot5-base)
**Paper**: [BioT5: Enriching Cross-modal Integration in Biology with Chemical Knowledge and Natural Language Associations](https://arxiv.org/abs/2310.07276)

Key info from source:
- **Input format**: Task prefix + SELFIES string or text description
- **Max tokens**: 512
- **License**: MIT
- **Architecture**: T5-base (300M params)
- **Tasks**: mol2text, text2mol, caption

## How The Server Works

- **Pattern**: Custom FastAPI generation server with HuggingFace Transformers
- **Container**: `python:3.11-slim` — installs deps at every startup (no venv/PVC pattern)
- **No PVC**: Uses RawDeployment, installs pip deps every restart (~3-5 min cold start)
- **ConfigMap**: `biot5-server` — server code embedded in inferenceservice.yaml
- **Health**: Custom `/health` endpoint
- **CPU only**: No GPU allocation
- **Deployment mode**: RawDeployment (not Serverless)
- **Output**: Custom `/v1/science/generate` response format

## Gateway Integration

- **k8s ISVC name**: `biot5`
- **API model ID**: `biot5` (no mapping in ISVC_NAME_MAP)
- **MODEL_TYPE**: defaults to "chat" — needs update to "generate"
- **KSERVE_CUSTOM_MODELS**: not listed — needs addition
- **Scale-to-zero**: minReplicas=0 (RawDeployment)

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/biot5/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=biot5

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=biot5 -c kserve-container -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/science/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"biot5","task":"mol2text","input":"[C][Branch1][Branch1][=N][Branch1][C][=O][NH1][C][Branch1][Branch1][C][Branch1][C][=O][OH1]"}'
```

## Known Issues / Optimization Opportunities

1. **No venv/PVC pattern**: Installs pip deps every restart (~3-5 min cold start). Should use venv-on-PVC for fast restarts.

2. **transformers==4.44.2 pinned**: Specific version pinned in pip install. Should keep updated but pinning is good practice.

3. **CPU only**: Reasonable for 300M T5 model. Could add GPU for batch inference.

4. **No PVC**: Model and deps not persisted. Every restart requires full download and install.

5. **Gateway registration incomplete**: Model not in MODEL_TYPES, MODEL_METADATA, KSERVE_CUSTOM_MODELS, or CONTEXT_WINDOWS in gateway.py.

6. **RawDeployment mode**: Does not use Knative scaling. Consider Serverless for scale-to-zero.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap + ISVC spec (no PVC) |
| `kustomization.yaml` | Kustomize resources |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
