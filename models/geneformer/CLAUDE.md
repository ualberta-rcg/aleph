# Geneformer Model Deployment

## What this model does
Geneformer from NIH NCI is a context-aware gene network inference model. Pretrained on 30M single-cell transcriptomes. V2-104M variant. Takes ranked gene token IDs.

## Source
- **HF**: ctheodoris/Geneformer | **License**: BSD-2-Clause | **Params**: 104M

## How the server works
- `POST /v1/embed` -- accepts `gene_ids` (ranked gene token IDs, max 4096)
- Returns mean-pooled cell embeddings
- Uses AutoModel with trust_remote_code

## Our config vs source
- Downloads Geneformer-V2-104M subdirectory only
- venv-on-PVC, torch CUDA, GPU shared (L40S-SHARED), 5Gi PVC
- minReplicas: 0, startup/readiness probes configured

## Deploy/update/test
```bash
kubectl apply -k models/geneformer/
kubectl get inferenceservice geneformer -n models
```

## Gateway integration
- MODEL_TYPES: `"geneformer": "embedding"` | KServe custom | Not in MODEL_METADATA

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
