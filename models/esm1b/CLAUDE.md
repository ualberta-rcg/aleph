# ESM-1b Model Deployment

## What this model does
ESM-1b is a 650M parameter protein language model from Meta. Produces embeddings for protein sequences. Predecessor to ESM-2 but still widely used.

## Source
- **HF**: facebook/esm1b_t33_650M_UR50S
- **License**: MIT
- **Parameters**: 650M

## How the server works
- FastAPI server embedded as ConfigMap (`esm1b-server`)
- `POST /v1/embeddings` -- accepts `input` or `sequences`, returns mean-pooled embeddings
- Uses AutoTokenizer + EsmModel, fp16 on GPU
- max_length=1024 truncation

## Our config vs source
- venv-on-PVC, torch>=2.6 CUDA
- Pre-downloads model in init container
- GPU shared (L40S-SHARED), minReplicas: 0
- 5Gi PVC

## Deploy/update/test commands
```bash
kubectl apply -k models/esm1b/
kubectl get inferenceservice esm1b -n models
```

## Gateway integration
- MODEL_TYPES: `"esm1b": "embedding"`
- Not in MODEL_METADATA (needs adding)
- KServe custom model

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
