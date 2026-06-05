# ProtGPT2 — Protein Sequence Generation

## Source
- HuggingFace: https://huggingface.co/nferruz/ProtGPT2
- License: MIT

## Deployment Summary
- **Model**: ProtGPT2 (~1.5B params)
- **GPU**: 1x L40S (shared), ~2GB VRAM
- **PVC**: protgpt2-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/completions` — generate protein sequences
- Input: prompt (partial amino acid), max_tokens, temperature
- Output: generated protein sequences

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC (all-in-one)
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- transformers (GPT2LMHeadModel, AutoTokenizer)
- torch (CUDA)

## Gateway Integration
- ISVC name: `protgpt2`
- MODEL_TYPE: chat
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: not listed (should be added)

## Audit Notes
- Lightweight model (~2GB VRAM) — can run on GPU slices
- Standard GPT-2 architecture adapted for protein vocabulary
- 28K downloads on HuggingFace
- No separate PVC file

## Update Reminder
- Check for ProtGPT2 v2 or larger variants
- Monitor nferruz/ProtGPT2 for updates
