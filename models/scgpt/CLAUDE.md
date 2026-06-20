# scGPT -- Model Context

## What This Model Does

scGPT (bowang-lab/scGPT) is a foundation model for single-cell gene expression data, trained on 33 million cells. Takes gene name + expression value pairs as input and returns 512-dimensional cell embeddings (mean-pooled). Uses a TransformerModel architecture with gene tokenization via GeneVocab. Useful for cell type annotation, batch correction, gene perturbation prediction, and multi-omic integration.

**2026-06-19:** v2 Template-C card; added `/v1/science/embed` route alias (was `/v1/embeddings` only, OpenAI-style). Non-text (gene expression) → primary `/v1/science/embed`, `/v1/embeddings` kept secondary. Confirmed GPU (L40S slice 10 GiB, gpumem). 6-check test.py added.

## Source Repo

**GitHub**: [bowang-lab/scGPT](https://github.com/bowang-lab/scGPT)

- **HuggingFace weights**: [tdc/scGPT](https://huggingface.co/tdc/scGPT)
- **License**: MIT
- **Architecture**: Transformer (12 layers, 8 heads, 512 hidden dim, 512 FFN dim)
- **Parameters**: ~50M
- **Paper**: "scGPT: toward building a foundation model for single-cell multi-omics using generative AI" (Cui et al., 2024)

## How The Server Works

- **Pattern**: Custom FastAPI + venv on PVC
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`
- **Init container**: Creates/updates venv (with import validation check), installs torch==2.1.2 (cu121), torchtext==0.16.2, numpy<2.0, scgpt, fastapi, uvicorn, huggingface_hub, downloads weights from tdc/scGPT
- **ConfigMap**: Server code embedded as `scgpt-server` ConfigMap, mounted at `/app/`
- **PVC**: `scgpt-data` (15Gi, NFS) -- stores venv + model weights + vocab
- **Health**: Custom `/health` endpoint returns `{"status": "ok|loading", "model": "scgpt", "device": "cuda|cpu"}`
- **GPU**: 1x L40S-SHARED (time-sliced), fp32 inference
- **Startup**: ~2-3 minutes
- **Vocab loading**: Loads vocab.json from model dir, falls back to scgpt package default, adds special tokens (<pad>, <cls>, <eoc>)
- **Embedding**: Uses `model._encode(gene_ids, values)` with mean pooling

## Our Config vs Source Recommendations

| Aspect | Source | Our Config | Notes |
|--------|--------|-----------|-------|
| Model loading | Full fine-tuning API | Inference-only (eval mode) | Correct for embeddings |
| Gene tokenization | GeneVocab | GeneVocab with fallbacks | Handles missing genes with <pad> |
| Embedding extraction | Various methods | `_encode()` + mean pool | Standard approach |
| Precision | fp32 | fp32 | Correct for small model |
| Batch size | Variable | 1 (sequential) | No batch support |

## Gateway Integration

- **ISVC name**: `scgpt` (maps to API id `scgpt`)
- **MODEL_TYPE**: embedding
- **KSERVE_CUSTOM_MODELS**: yes -- uses `/v1/` prefix
- **GPU_MODELS**: yes
- **CONTEXT_WINDOWS**: 512
- **Scale-to-zero**: minReplicas=0, scaleTarget=3, 900s retention
- **Custom health probe**: yes (in `_CUSTOM_HEALTH_MODELS`)
- **Startup time estimate**: 2-3 minutes

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/scgpt/

# Force update
kubectl apply --server-side --force-conflicts -k models/scgpt/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=scgpt

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=scgpt -c kserve-container -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"scgpt","input":{"genes":["CD3D","IL7R","CCR7","CD8A"],"values":[3.5,0.0,1.2,0.8]}}'
```

## Known Issues / Optimization Opportunities

1. **Venv rebuild logic**: Init container rebuilds venv if `import fastapi, scgpt; numpy<2` check fails. This is a smart approach but could trigger unexpected rebuilds.

2. **Missing gene handling**: Unknown genes are mapped to `<pad>` token. Could log or warn about unknown genes.

3. **torch==2.1.2 pin**: Older torch version pinned for scgpt compatibility. May need updating as scgpt evolves.

4. **numpy<2.0 pin**: Required for scgpt compatibility. Correctly enforced.

5. **Empty cell handling**: Returns zero vector (512-dim zeros) for cells with no genes/values. Could return an error instead.

6. **No batch support**: Processes cells sequentially. Could batch for throughput.

7. **Init container idempotent**: Yes -- validates venv via import check, checks model/vocab.json before downloading.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap (server.py) + ISVC spec |
| `kustomization.yaml` | Kustomize resources + configMapGenerator |
| `pvc.yaml` | Dedicated PVC (scgpt-data, 15Gi NFS) |
| `server.py` | Extracted server code (actual code lives in ConfigMap via kustomize configMapGenerator) |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml, server.py), update details.yaml to match.**
