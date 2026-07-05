# SaProt 650M Model Deployment

## What this model does
SaProt 650M from Westlake University combines amino acid and 3Di structure tokens in a single vocabulary. Structure-aware protein embeddings. ESM-2 backbone.

## Source
- **HF**: westlake-repl/SaProt_650M_AF2 | **License**: MIT | **Params**: 650M

## How the server works
- `POST /v1/embeddings` -- protein sequences with optional 3Di tokens (e.g., 'M#a#K#b#')
- EsmTokenizer + EsmModel from local `/data/model` directory
- Mean-pooled embeddings, fp16 on GPU

## Our config vs source
- Weights downloaded via snapshot_download to PVC
- HF_TOKEN required
- GPU shared (L40S-SHARED), 10Gi PVC `saprot-650m` (bare fleet naming, was `saprot-650m-data`/`model-data`), minReplicas: 1 (always-on)

## Deploy/update/test
```bash
kubectl apply -f models/saprot-650m/pvc.yaml
kubectl apply -f models/saprot-650m/inferenceservice.yaml
kubectl apply -f models/saprot-650m/details.yaml
kubectl get inferenceservice saprot-650m -n models
```

## Gateway integration
- MODEL_TYPES: `"saprot-650m": "embedding"` | KServe custom | Not in MODEL_METADATA

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
