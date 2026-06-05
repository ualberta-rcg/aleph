# MatterSim — Microsoft Universal Atomistic Force Field

## Source
- HuggingFace: https://huggingface.co/microsoft/mattersim
- Paper: arxiv 2405.04967
- License: MIT

## Deployment Summary
- **Model**: MatterSim v1.0.0-1M (~1M params)
- **GPU**: 1x L40S (shared), falls back to CPU
- **PVC**: mattersim-data (10Gi NFS)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/science/predict` — predict energy, forces, stress
- `POST /v1/science/relax` — relax atomic structure with BFGS optimizer
- Input: elements, positions, lattice
- Output: energy (eV), forces (eV/Ang), stress (eV/Ang^3 and GPa)

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + PVC + ISVC (all-in-one)
- `details.yaml` — model metadata ConfigMap

## Dependencies
- mattersim (pip)
- torch >= 2.2.0 (CUDA 12.6)
- torch_geometric >= 2.5.3 (PyG)
- ase, fastapi, uvicorn

## Gateway Integration
- ISVC name: `mattersim`
- MODEL_TYPE: force-field
- KSERVE_CUSTOM_MODELS: yes (listed in gateway)
- GPU_MODELS: not explicitly listed (should be added)

## Audit Notes
- Requires git + build-essential in init container for PyG compilation
- Uses TORCH_HOME=/data/torch_cache for checkpoint caching
- Provides both predict and relax endpoints (unique among force fields)
- Uses NFS (ReadWriteMany) PVC — unusual for force field models

## Update Reminder
- Check for new MatterSim checkpoint releases
- Monitor mattersim pip package updates
- Consider adding to GPU_MODELS in gateway
