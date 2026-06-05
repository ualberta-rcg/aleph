# UMA-M Model Deployment

## What this model does
UMA-M is a universal materials potential from Meta FAIR using EquiformerV2 backbone. Predicts energy, forces, and stress for atomic structures. ~1.1B parameters. Non-commercial license.

## Source
- **HF**: facebook/UMA | **License**: Meta Research License (non-commercial) | **Params**: ~1.1B

## How the server works
- `POST /v1/science/predict` -- accepts `elements`, `positions`, `lattice`, `task`
- Uses fairchem-core OCPCalculator + ASE Atoms
- Returns energy (eV), forces (eV/A), stress tensor

## Our config vs source
- venv-on-PVC with fairchem-core>=2.0, ASE, torch CUDA
- Checkpoint ~4.5GB downloaded from HF
- GPU shared (L40S-SHARED), 30Gi PVC, minReplicas: 0

## Deploy/update/test
```bash
kubectl apply -k models/uma-m/
kubectl get inferenceservice uma-m -n models
```

## Gateway integration
- MODEL_TYPES: not registered (needs adding as "force-field")
- Not in MODEL_METADATA | Not in GPU_MODELS

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
