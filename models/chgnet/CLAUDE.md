# CHGNet — Universal Neural Network Potential with Magnetic Moments

## Source
- GitHub: https://github.com/CederGroupHub/chgnet
- HuggingFace: CederGroupHub/chgnet
- License: MIT

## Deployment Summary
- **Model**: CHGNet v0.3 (~2M params)
- **GPU**: 1x L40S (shared)
- **PVC**: chgnet-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/science/energy` — predict energy, forces, stress from atomic structure
- Input: structure dict with elements, positions, cell, pbc
- Output: energy_eV, forces_eV_A, stress_eV_A3

## Key Files
- `inferenceservice.yaml` — ISVC spec (server ConfigMap is separate: chgnet-server)
- `pvc.yaml` — chgnet-data PVC
- `server.py` — server code (deployed as ConfigMap)
- `kustomization.yaml` — kustomize resources

## Dependencies
- chgnet (pip, includes torch)
- fastapi, uvicorn, huggingface_hub

## Gateway Integration
- ISVC name: `chgnet` -> API name: `chgnet-v0.3` (via ISVC_NAME_MAP)
- MODEL_TYPE: force-field
- CONTEXT_WINDOWS: chgnet-v0.3 -> 0
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: not listed (should be added)

## Audit Notes
- One of the earlier deployed models (from audit batch)
- Server code is in a separate server.py file (not embedded in ISVC)
- HF_TOKEN required for checkpoint download
- Uses chgnet pip package which auto-downloads weights

## Update Reminder
- Check for new CHGNet versions
- Monitor CederGroupHub/chgnet GitHub for updates
- Consider adding to GPU_MODELS in gateway
