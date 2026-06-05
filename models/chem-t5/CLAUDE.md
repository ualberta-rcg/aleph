# Chem-T5 — Model Context

## What This Model Does

Chem-T5 by IBM GT4SD. ~250MB T5 model for multitask text and chemistry. Handles retrosynthesis (predict reactants), forward synthesis (predict products), molecular captioning (SMILES to text), text-to-SMILES generation, and paragraph-to-actions conversion. Max sequence length 512 tokens.

## Source Repo

**HuggingFace**: [GT4SD/multitask-text-and-chemistry-t5-base-standard](https://huggingface.co/GT4SD/multitask-text-and-chemistry-t5-base-standard)

Key info from source:
- **Input format**: Task prefix + SMILES string or text description
- **Max tokens**: 512
- **License**: MIT
- **Architecture**: T5-base (~60M params)
- **Tasks**: forward_synthesis, retrosynthesis, caption, generate, paragraph_to_actions

## How The Server Works

- **Pattern**: Custom FastAPI generation server with HuggingFace Transformers
- **Container**: `python:3.11-slim` — installs deps at every startup (no venv/PVC pattern)
- **No PVC**: Uses RawDeployment, installs pip deps every restart (~3-5 min cold start)
- **ConfigMap**: `chem-t5-server` — server code embedded in inferenceservice.yaml
- **Health**: Custom `/health` endpoint
- **CPU only**: No GPU allocation. Small model runs fine on CPU.
- **Deployment mode**: RawDeployment (not Serverless)
- **Output**: Custom `/v1/science/generate` response format

## Gateway Integration

- **k8s ISVC name**: `chem-t5`
- **API model ID**: `chem-t5` (no mapping in ISVC_NAME_MAP)
- **MODEL_TYPE**: defaults to "chat" — needs update to "generate"
- **KSERVE_CUSTOM_MODELS**: not listed — needs addition
- **Scale-to-zero**: minReplicas=0 (RawDeployment)

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/chem-t5/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=chem-t5

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=chem-t5 -c kserve-container -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/science/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"chem-t5","task":"forward_synthesis","input":"CC(=O)Oc1ccccc1C(=O)O.CCO"}'
```

## Known Issues / Optimization Opportunities

1. **No venv/PVC pattern**: Installs pip deps every restart (~3-5 min cold start). Should use venv-on-PVC for fast restarts.

2. **transformers==4.44.2 pinned**: Specific version pinned. Should keep updated.

3. **No model caching**: Model downloaded from HF at runtime each restart. No PVC for persistence.

4. **Gateway registration incomplete**: Model not in MODEL_TYPES, MODEL_METADATA, KSERVE_CUSTOM_MODELS, or CONTEXT_WINDOWS in gateway.py.

5. **RawDeployment mode**: Does not use Knative scaling.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap + ISVC spec (no PVC) |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
