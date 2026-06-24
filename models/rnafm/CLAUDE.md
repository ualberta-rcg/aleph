# RNA-FM Model Deployment

## What this model does
RNA-FM from multimolecule is a 100M parameter foundation model trained on 23.7M ncRNA sequences from RNAcentral. Embeddings for non-coding RNA functional prediction.

## Source
- **HF**: multimolecule/rnafm | **License**: RNA-FM License (non-commercial) | **Params**: 100M

## How the server works
- `POST /v1/science/embed` -- RNA sequence(s) to mean-pooled embeddings
- Uses RnaTokenizer + RnaFmModel from multimolecule
- max_length=1024

## Our config vs source
- venv-on-PVC with multimolecule + transformers
- GPU shared (L40S-SHARED), 5Gi PVC, minReplicas: 0
- HF_HUB_OFFLINE=1 in main container

## Deploy/update/test
```bash
kubectl apply -f models/rnafm/pvc.yaml
kubectl apply -f models/rnafm/inferenceservice.yaml
kubectl apply -f models/rnafm/details.yaml
kubectl get inferenceservice rnafm -n models

# Test externally via gateway VIP + Tyk auth
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/rnafm/test.py
```

## Gateway integration
- MODEL_TYPES: `"rnafm": "embedding"` | KServe custom | Not in MODEL_METADATA

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
