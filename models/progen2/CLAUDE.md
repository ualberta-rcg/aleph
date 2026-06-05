# ProGen2 — Protein Sequence Generation

## Source
- HuggingFace: https://huggingface.co/hugohrban/progen2-xlarge
- License: BSD-3-Clause

## Deployment Summary
- **Model**: ProGen2-XLarge (6.4B params)
- **GPU**: 1x L40S (shared), ~13GB VRAM required
- **PVC**: progen2-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/completions` — generate protein sequences
- Input: prompt (partial amino acid sequence), max_tokens, temperature
- Output: generated protein sequences

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC (all-in-one)
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- transformers (AutoModelForCausalLM with trust_remote_code)
- torch (CUDA)

## Gateway Integration
- ISVC name: `progen2`
- MODEL_TYPE: chat
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: not listed (should be added)

## Audit Notes
- Large model (6.4B params) requires significant VRAM
- Uses trust_remote_code=True for custom model architecture
- BSD-3-Clause license
- No separate PVC file

## Update Reminder
- Check for ProGen2 updates or larger variants
- Monitor hugohrban/progen2-xlarge for model updates
