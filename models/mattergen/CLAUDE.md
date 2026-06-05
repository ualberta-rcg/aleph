# MatterGen — Microsoft Crystal Structure Generation

## Source
- HuggingFace: https://huggingface.co/microsoft/mattergen
- Paper: Nature 2025
- License: MIT

## Deployment Summary
- **Model**: MatterGen base (45M params)
- **GPU**: 1x L40S (shared)
- **PVC**: mattergen-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: /data/mg-venv (separate from main venv)
- **Timeout**: 600s (generation is slow)

## API
- `POST /v1/science/generate` — generate crystal structures
- Input: chemical_system, num_structures, checkpoint
- Output: array of CIF format crystal structures

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + PVC (all-in-one)
- `pvc.yaml` — mattergen-data PVC
- `kustomization.yaml` — kustomize resources

## Dependencies
- torch 2.2.1 (CUDA 11.8)
- torch_geometric >= 2.5
- mattergen (cloned from GitHub, editable install)
- ase, pymatgen, pytorch_lightning, hydra-core, omegaconf, wandb, fire, emmet-core, mp-api

## Architecture Notes
- Uses subprocess to call mattergen-generate CLI
- Requires cloned GitHub repo at /data/model/repo
- HF checkpoint at /data/model/checkpoints/mattergen_base
- Complex dependency chain: PyTorch -> PyG -> mattergen

## Gateway Integration
- ISVC name: `mattergen`
- MODEL_TYPE: generate
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: yes

## Audit Notes
- Uses older CUDA 11.8 (torch 2.2.1) — newer models use CUDA 12.6
- Generation uses subprocess (suboptimal but works)
- Long timeout (600s) due to diffusion sampling
- HF_TOKEN required for model download

## Update Reminder
- Check for newer MatterGen releases with API improvements
- Consider migrating to CUDA 12.6 for consistency
- Monitor mattergen GitHub for CLI changes
