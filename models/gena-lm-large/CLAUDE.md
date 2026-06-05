# GENA-LM-large Model Deployment

## What this model does
GENA-LM-large from AIRI Institute is a 340M DNA BERT trained on hg38+T2T human genome. Handles up to 36kb context. Uses CLS token embedding (not mean pooling).

## Source
- **HF**: AIRI-Institute/gena-lm-bert-large-t2t | **License**: Apache-2.0 | **Params**: 340M

## How the server works
- `POST /v1/science/embed` -- DNA sequence(s) to CLS-token embeddings
- Uses hidden[:, 0, :] (CLS token) instead of mean pooling
- max_length=512 truncation

## Our config vs source
- venv-on-PVC with transformers<4.45
- Downloads model to `/data/model`
- GPU shared (L40S-SHARED), 5Gi PVC, minReplicas: 0
- HF_HUB_OFFLINE=1 in main container

## Deploy/update/test
```bash
kubectl apply -k models/gena-lm-large/
kubectl get inferenceservice gena-lm-large -n models
```

## Gateway integration
- MODEL_TYPES: `"gena-lm-large": "embedding"` | KServe custom | Not in MODEL_METADATA

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
