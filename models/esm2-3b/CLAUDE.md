# ESM-2 3B -- Model Context

## What This Model Does

ESM-2 3B (facebook/esm2_t36_3B_UR50D) is Meta's large protein language model trained on UniRef50 with a masked language modelling objective. It produces 2560-dimensional mean-pooled embeddings from amino acid sequences. Higher accuracy than smaller ESM-2 checkpoints (650M, 150M, etc.) for structure prediction, function annotation, and variant effect prediction. Max 1022 residues.

## Source Repo

**HuggingFace**: [facebook/esm2_t36_3B_UR50D](https://huggingface.co/facebook/esm2_t36_3B_UR50D)

- **Framework**: HuggingFace Transformers (`EsmModel`)
- **Model size**: ~12 GB weights on disk
- **License**: MIT
- **Max sequence**: 1022 amino acids (ESM-2 token limit)

## How The Server Works

- **Pattern**: Custom FastAPI + venv on PVC
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`
- **Init container**: Creates venv, installs deps (torch, transformers, fastapi, uvicorn, huggingface_hub), downloads model from HF
- **ConfigMap**: Server code embedded as `esm2-3b-server` ConfigMap, mounted at `/app/`
- **PVC**: `esm2-3b-data` (30Gi, NFS) -- stores venv + model weights
- **Health**: Custom `/health` endpoint returns `{"status": "ok|loading", "device": "cuda|cpu"}`
- **GPU**: 1x L40S-SHARED (time-sliced), fp16 inference
- **Startup**: ~4-5 minutes (model loading into GPU)
- **Embeddings**: Mean-pooled over last hidden state with attention mask weighting

## Our Config vs Source Recommendations

| Aspect | Source | Our Config | Notes |
|--------|--------|-----------|-------|
| Precision | fp32 | fp16 (GPU) | Halves VRAM, acceptable accuracy loss |
| Pooling | CLS token or mean | Mean-pooled with attention mask | Standard practice |
| Batch | Variable | 1 | No batch support in server |
| Max length | 1022 | 1022 | Matches ESM-2 token limit |

## Gateway Integration

- **ISVC name**: `esm2-3b` (maps to API id `esm2-3b`)
- **MODEL_TYPE**: embedding
- **KSERVE_CUSTOM_MODELS**: yes -- uses `/v1/` prefix
- **GPU_MODELS**: yes
- **CONTEXT_WINDOWS**: 1022
- **Scale-to-zero**: minReplicas=0, scaleTarget=3, 900s retention
- **Custom health probe**: yes (in `_CUSTOM_HEALTH_MODELS`)
- **Startup time estimate**: 4-5 minutes

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/esm2-3b/

# Force update (if ConfigMap changed)
kubectl apply --server-side --force-conflicts -k models/esm2-3b/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=esm2-3b

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=esm2-3b -c kserve-container -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"esm2-3b","input":"MKTVRQERLKSIVRILERSKEPVSGAQ"}'
```

## Known Issues / Optimization Opportunities

1. **Unpinned pip dependencies**: Init container installs `torch transformers fastapi uvicorn huggingface_hub` without version pins. Could break on rebuild.

2. **No batching**: Server processes sequences one at a time. Could add batch support for throughput improvement.

3. **Missing sequence validation**: No server-side check that input is valid amino acid characters or within length limits.

4. **fp16 on shared GPU**: Running fp16 on time-sliced L40S is fine but could consider fp32 for maximum accuracy if VRAM allows.

5. **readOnly volume**: PVC is mounted readOnly for main container (good practice).

6. **Init container idempotent**: Yes -- checks for venv/bin and model/config.json before installing/downloading.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap (server.py) + ISVC spec |
| `kustomization.yaml` | Kustomize resources + configMapGenerator |
| `pvc.yaml` | Dedicated PVC (esm2-3b-data, 30Gi NFS) |
| `server.py` | Extracted server code (actual code lives in ConfigMap via kustomize configMapGenerator) |
| `README.md` | Original documentation |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml, server.py), update details.yaml to match.**
