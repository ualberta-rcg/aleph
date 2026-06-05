# ESMfold — Model Context

## What This Model Does

ESMfold is Meta's end-to-end protein folding model. Predicts 3D protein structures from amino acid sequences without requiring MSA (Multiple Sequence Alignment) lookup or external sequence databases. Based on the ESM-2 backbone (~690M params). Returns PDB-formatted structures with pLDDT confidence scores. Single-sequence method — much faster than AlphaFold2 but potentially less accurate for sequences with few homologs.

## Source Repo

**HuggingFace**: [facebook/esmfold_v1](https://huggingface.co/facebook/esmfold_v1)

- **Framework**: HuggingFace Transformers (`EsmForProteinFolding`)
- **Model size**: 8.44 GB weights file
- **License**: MIT
- **Max sequence**: 1022 amino acids (ESM-2 token limit)

## How The Server Works

- **Pattern**: Custom FastAPI + venv on PVC
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`
- **Init container**: Creates venv, installs deps (numpy<2, torch, transformers, etc.), downloads model from HF
- **ConfigMap**: Server code embedded as `esmfold-server` ConfigMap, mounted at `/app/`
- **PVC**: `esmfold-data` — stores venv + model weights
- **Health**: Custom `/health` endpoint returns `{"status": "ok|loading", "model": "esmfold"}`
- **GPU**: 1× L40S, auto-detects cuda/cpu
- **Startup**: ~3 minutes (model loading into GPU)

## Gateway Integration

- **ISVC name**: `esmfold` (matches API id)
- **MODEL_TYPE**: structure
- **KSERVE_CUSTOM_MODELS**: yes — uses `/v1/` prefix
- **GPU_MODELS**: yes
- **Scale-to-zero**: minReplicas=0, scaleTarget=3, 900s retention after scale-down

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/esmfold/

# Force update (if ConfigMap changed)
kubectl apply --server-side --force-conflicts -k models/esmfold/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=esmfold

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=esmfold -c kserve-container -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/structure \
  -H "Content-Type: application/json" \
  -d '{"sequence": "MKTVRQERLKSIVRILERSKEPVSGAQ"}'
```

## Known Issues / Optimization Opportunities

1. **FP32 on GPU**: Model runs in FP32 (`model.to(device)` without dtype argument). Could use FP16 to halve VRAM usage and speed up inference. ESMfold's config.json has `fp16_esm: false` — consider enabling it.

2. **numpy<2 pinning**: Init container installs `numpy<2`. This is required because numpy 2.x breaks `transformers.models.esm.openfold_utils.protein` format spec handling. The server.py in the ConfigMap includes a monkey-patch for this, but the simpler fix is the version pin.

3. **No batching**: Server processes one sequence at a time. Could add batch support for throughput.

4. **Missing error handling for long sequences**: No server-side validation that sequence length ≤ 1022. Very long sequences will crash or produce garbage.

5. **Pip dependencies unpinned**: Init container installs `torch transformers protobuf` without version pins. Could break on rebuild. Consider pinning versions.

6. **readOnly volume mount**: PVC is mounted readOnly for the main container (good — prevents accidental writes during inference).

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap (server.py) + ISVC spec |
| `kustomization.yaml` | Kustomize resources + configMapGenerator |
| `pvc.yaml` | Dedicated PVC (esmfold-data) |
| `server.py` | Extracted server code (actual code lives in ConfigMap via kustomize configMapGenerator) |
| `README.md` | This model's documentation |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml, server.py), update details.yaml to match.**
