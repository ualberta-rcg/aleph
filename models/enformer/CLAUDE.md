# Enformer Model Deployment

## What this model does
Enformer predicts gene expression (regulatory track values) from 196,608 bp DNA sequences. Trained by DeepMind on human and mouse data. Predicts 5313 human + 1643 mouse tracks. Tier 1 model.

## Source
- **HF**: EleutherAI/enformer-official-rough | **License**: CC-BY-4.0 | **Params**: ~500M

## How the server works
- `POST /v1/science/predict` -- accepts `sequence` (~196kb), `organism` (human|mouse), `return_tracks`
- One-hot encodes DNA, pads to 196,608 bp
- Returns human/mouse predictions (896 bins x N tracks)

## Our config vs source
- Pinned transformers>=4.28,<4.38 for enformer-pytorch compatibility
- venv-on-PVC, 10Gi PVC, minReplicas: 0
- GPU assigned but no nodeSelector (can run on any GPU node)
- 16Gi/32Gi memory, 8 CPU cores, timeout 595s
- HF_HUB_OFFLINE=1 in main container

## Deploy/update/test
```bash
kubectl apply -k models/enformer/
kubectl get inferenceservice enformer -n models
```

## Gateway integration
- MODEL_TYPES: `"enformer": "predict"` | KServe custom | Not in MODEL_METADATA

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
