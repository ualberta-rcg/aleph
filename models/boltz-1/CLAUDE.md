# Boltz-1 Model Deployment

## What this model does
Boltz-1 from boltz-community predicts 3D structures of proteins, RNA, DNA, small molecules, and glycans. AlphaFold3-class capability. MIT license. Tier 1 model.

## Source
- **HF**: boltz-community/boltz-1 (https://huggingface.co/boltz-community/boltz-1)
- **License**: MIT
- **Parameters**: ~8B
- **Weights**: boltz1.ckpt (6.9GB) + boltz1_conf.ckpt (3.6GB)

## How the server works
- FastAPI server embedded as ConfigMap (`boltz-1-server`)
- Runs `boltz predict` CLI via subprocess
- `POST /v1/science/predict` -- accepts `sequence`, `type` (protein|rna|dna), `demo`, `use_msa_server`
- Returns PDB content, pLDDT, mean pLDDT, confidence JSON
- Uses MSA server by default

## Our config vs source
- RawDeployment mode, 1x L40S
- No venv -- installs pip packages at runtime in main container (torch, boltz)
- 25Gi PVC (ReadWriteMany for nfs-client)
- Sentinel file for idempotent init
- Weights downloaded from HF (~10.5GB total)
- timeout: 600s, maxReplicas: 1

## Deploy/update/test commands
```bash
kubectl apply -k models/boltz-1/
kubectl get inferenceservice boltz-1 -n models
```

## Gateway integration
- MODEL_TYPES: `"boltz-1": "structure"`
- Not in MODEL_METADATA (needs adding)
- ISVC name = API name: `boltz-1`

## Known Issues
- Runtime pip install in main container (slow cold start ~3-5 min)
- PDB output capped at 50KB
- No pip version pins

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
