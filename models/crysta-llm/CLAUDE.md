# CrystaLLM — Crystal Structure Generation via Language Model

## Source
- HuggingFace (model): https://huggingface.co/c-bone/CrystaLLM-pi_base
- HuggingFace (tokenizer): https://huggingface.co/lantunes/CrystaLLM
- License: MIT

## Deployment Summary
- **Model**: CrystaLLM-pi_base (~25M params, GPT-2 based)
- **GPU**: 1x L40S (shared)
- **PVC**: crysta-llm-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)
- **Timeout**: 300s

## API
- `POST /v1/science/generate` — generate crystal structures from formula
- Input: formula, temperature, max_new_tokens, num_samples
- Output: array of CIF-format crystal structure strings

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py + tokenizer) + PVC + ISVC (all-in-one)
- `pvc.yaml` — crysta-llm-data PVC
- `README.md` — model documentation
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- transformers (GPT2LMHeadModel)
- torch
- Custom CIFTokenizer (embedded in ConfigMap)
- fastapi, uvicorn

## Gateway Integration
- ISVC name: `crysta-llm`
- MODEL_TYPE: chat
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: not listed (should be added)

## Audit Notes
- Very small model (25M params)
- Custom character-level tokenizer for CIF format (vocab=377)
- Tokenizer code embedded as separate ConfigMap
- Formula conditioning via text generation prompt

## Update Reminder
- Check for larger CrystaLLM variants
- Monitor c-bone/CrystaLLM-pi_base for updates
