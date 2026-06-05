# MACE-MH-1 — Multi-Head Foundation Force Field

## Source
- HuggingFace: https://huggingface.co/mace-foundations/mace-mh-1
- License: ASL (academic/non-commercial)
- Architecture: MACE multi-head equivariant MPNN

## Deployment Summary
- **Model**: MACE-MH-1 (~50M params, 7 heads)
- **GPU**: 1x L40S (shared), falls back to CPU
- **PVC**: mace-mh-1-data (5Gi NFS ReadWriteMany)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)
- **Sentinel**: /data/venv/.mace-mh1-ready

## API
- `POST /v1/science/predict` — predict energy, forces, stress with selectable head
- Input: elements, positions, lattice (optional), head selection
- Output: energy_eV, forces_eV_per_Ang, stress_eV_per_Ang3
- 7 heads: omat_pbe (default), omol, spice_wB97M, rgd1_b3lyp, oc20_usemppbe, matpes_r2scan

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + PVC + ISVC (all-in-one)
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- mace-torch >= 0.3
- torch (CUDA 12.6)
- ase, fastapi, uvicorn, huggingface_hub

## Gateway Integration
- ISVC name: `mace-mh-1`
- MODEL_TYPE: force-field
- KSERVE_CUSTOM_MODELS: yes (listed in gateway)
- GPU_MODELS: not explicitly listed (should be added)

## Audit Notes
- Uses NFS (ReadWriteMany) PVC — unusual for single-replica models
- Heads are lazily loaded and cached in calc_cache dict
- License is ASL (academic/non-commercial) — not MIT like mace-mp-0

## Update Reminder
- Check for new MACE-MH-1 head releases
- Monitor mace-torch package for API changes
- Consider adding to GPU_MODELS in gateway
