# ESM2-150M Model Deployment

## What this model does
ESM2 150M is a mid-size protein encoder from Meta (150M, 30 layers). Good balance of speed and accuracy.

## Source
- **HF**: facebook/esm2_t30_150M_UR50D | **License**: MIT | **Params**: 150M

## How the server works
- `POST /v1/embeddings` -- protein sequence(s) to mean-pooled embeddings
- EsmModel, fp16 on GPU, max_length=1024

## Our config vs source
- venv-on-PVC, torch>=2.6 CUDA, GPU shared (L40S-SHARED), 3Gi PVC, minReplicas: 0

## Deploy/update/test
```bash
kubectl apply -k models/esm2-150m/
kubectl get inferenceservice esm2-150m -n models
```

## Gateway integration
- MODEL_TYPES: `"esm2-150m": "embedding"` | KServe custom | Not in MODEL_METADATA

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
