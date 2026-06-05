# MACE-MP — Universal ML Interatomic Potential

## Source
- HuggingFace: https://huggingface.co/ACEsuit/mace-mp-0
- License: MIT
- Architecture: MACE (Multi Atomic Cluster Expansion equivariant MPNN)

## Deployment Summary
- **Model**: MACE-MP-0b3-medium (~10M params, default), plus small and large variants
- **GPU**: 1x L40S (shared), falls back to CPU
- **PVC**: mace-mp-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)
- **Sentinel**: /data/venv/.mace-mp-ready

## API
- `POST /v1/science/predict` — predict energy, forces, stress from atomic structure
- Input: elements, positions, lattice (optional), model variant selection
- Output: energy (eV), forces (eV/Ang), stress (eV/Ang^3)

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + PVC + ISVC (all-in-one)
- `pvc.yaml` — mace-mp-data PVC
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- mace-torch >= 0.3
- torch (CUDA 12.6)
- ase (Atomic Simulation Environment)
- fastapi, uvicorn, huggingface_hub

## Gateway Integration
- ISVC name: `mace-mp` (k8s) -> API name: `mace-mp-0`
- ISVC_NAME_MAP: not listed (uses ISVC host directly)
- MODEL_TYPE: force-field
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: not listed (should be added)

## Audit Notes
- All three model variants (small/medium/large) downloaded to PVC
- Uses float64 precision for accurate force computation
- ConfigMap and PVC are embedded inside inferenceservice.yaml

## Update Reminder
- Check for new MACE-MP-0 checkpoint releases on ACEsuit/mace-mp-0
- Monitor mace-torch package updates for API changes
- Consider adding to GPU_MODELS in gateway if not present
