# LigandMPNN Model Deployment

## What this model does
LigandMPNN from Baker Lab (UW) designs optimal amino acid sequences given a protein backbone structure (PDB) and optional ligand atoms. CPU-capable. ~1.7M parameters.

## Source
- **GitHub**: dauparas/LigandMPNN | **HF**: dauparas/LigandMPNN | **License**: MIT

## How the server works
- `POST /v1/design` -- accepts PDB backbone, returns designed sequences
- Runs LigandMPNN CLI via subprocess (run.py)
- Supports model_type: ligand_mpnn, protein_mpnn, per_residue_label_membrane_mpnn

## Our config vs source
- CPU-only (no GPU needed for ~1.7M params)
- Clones GitHub repo + downloads weights from HF in init
- venv-on-PVC with torch CPU, fastapi, prody
- 10Gi PVC, minReplicas: 0, timeout: 600s

## Deploy/update/test
```bash
kubectl apply -k models/ligandmpnn/
kubectl get inferenceservice ligandmpnn -n models
```

## Gateway integration
- MODEL_TYPES: `"ligandmpnn": "design"` | KServe custom | Not in MODEL_METADATA

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
