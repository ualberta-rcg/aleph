# MACE-MP-0 — Universal ML Force Field (CPU variant)

## Source
- GitHub: https://github.com/ACEsuit/mace
- License: MIT
- Architecture: MACE equivariant MPNN

## Deployment Summary
- **Model**: MACE-MP-0 medium variant (~10M params)
- **GPU**: None (CPU-only deployment, uses mace_mp() convenience loader)
- **PVC**: mace-mp-0-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)
- **CPU**: 8 cores requested, 16 limit

## API
- `POST /v1/science/energy` — predict energy, forces, stress from atomic structure
- Input: structure dict with elements, positions, cell, pbc
- Output: energy_eV, forces_eV_A, stress_eV_A3

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + PVC (all-in-one)

## Dependencies
- mace-torch (includes mace_mp convenience function)
- torch (CPU-only build via --extra-index-url)
- ase, fastapi, uvicorn

## Gateway Integration
- ISVC name: `mace-mp-0`
- ISVC_NAME_MAP: not listed (no remapping needed)
- MODEL_TYPE: force-field
- KSERVE_CUSTOM_MODELS: yes
- CONTEXT_WINDOWS: mace-mp-0 -> 0

## Audit Notes
- CPU-only deployment (no GPU requested) — slower but more portable
- Uses mace_mp() convenience function which auto-downloads checkpoint
- Uses float32 precision (less accurate than mace-mp's float64)
- Separate deployment from mace-mp (which offers GPU + multiple model sizes)

## Update Reminder
- Check if this should be consolidated with mace-mp (the GPU variant)
- Consider upgrading to float64 for better accuracy
- Monitor mace-torch updates for API changes
