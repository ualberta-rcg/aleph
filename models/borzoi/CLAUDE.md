# Borzoi Model Deployment

## What this model does
Borzoi from Calico Research predicts RNA-seq signal from 524,288 bp genomic DNA sequences. Gene expression at base-pair resolution. Based on Enformer architecture. Tier 1 model.

## Source
- **HF**: johahi/borzoi-replicate-0 | **License**: CC-BY-4.0 | **Params**: ~500M

## How the server works
- `POST /v1/science/predict` -- DNA sequence (~524kb) to RNA-seq predictions
- One-hot encodes DNA, pads/truncates to 524,288 bp
- Returns center bins of predictions: (n_bins, n_tracks) matrix

## Our config vs source
- venv-on-PVC with borzoi-pytorch + transformers<4.51
- GPU shared (L40S-SHARED), 10Gi PVC, minReplicas: 0
- 8Gi/16Gi memory for 524kb sequences
- HF_HUB_OFFLINE=1 in main container

## Deploy/update/test
```bash
kubectl apply -k models/borzoi/
kubectl get inferenceservice borzoi -n models
```

## Gateway integration
- MODEL_TYPES: `"borzoi": "predict"` | KServe custom | Not in MODEL_METADATA

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
