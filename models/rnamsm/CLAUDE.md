# RNA-MSM Model Deployment

## What this model does
RNA-MSM from multimolecule is an MSA transformer-based RNA model (~96M). Trained on Rfam. Uses MSA context for improved secondary structure prediction.

## Source
- **HF**: multimolecule/rnamsm | **License**: AGPL-3.0 | **Params**: ~96M

## How the server works
- `POST /v1/science/embed` -- RNA sequence(s) to mean-pooled embeddings
- Uses RnaTokenizer + RnaMsmModel from multimolecule
- max_length=1024

## Our config vs source
- venv-on-PVC with multimolecule + transformers
- GPU shared (L40S-SHARED), 5Gi PVC, minReplicas: 0
- HF_HUB_OFFLINE=1 in main container

## Deploy/update/test
```bash
kubectl apply -f models/rnamsm/pvc.yaml
kubectl apply -f models/rnamsm/inferenceservice.yaml
kubectl apply -f models/rnamsm/details.yaml
kubectl get inferenceservice rnamsm -n models

# Test externally via gateway VIP + Tyk auth
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/rnamsm/test.py
```

## Gateway integration
- MODEL_TYPES: `"rnamsm": "embedding"` | KServe custom | Not in MODEL_METADATA

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
