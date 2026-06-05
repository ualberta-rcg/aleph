# LeanDojo — Lean 4 Theorem Prover Premise Retriever

## Source
- HuggingFace: https://huggingface.co/kaiyuy/leandojo-lean4-retriever-byt5-small
- Paper: NeurIPS 2023
- License: Apache 2.0

## Deployment Summary
- **Model**: LeanDojo retriever ByT5-small (125M params)
- **GPU**: 1x L40S (shared)
- **PVC**: leandojo-data
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/science/retrieve` — retrieve relevant premises for a Lean 4 proof goal
- Input: goal (Lean 4 tactic state), num_premises
- Output: ranked premises with relevance scores

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + PVC + ISVC (all-in-one)
- `pvc.yaml` — leandojo-data PVC
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- transformers (AutoTokenizer, AutoModelForSeq2SeqLM)
- torch
- fastapi, uvicorn

## Gateway Integration
- ISVC name: `leandojo`
- MODEL_TYPE: embed
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: yes
- Listed in MODEL_METADATA

## Audit Notes
- Byte-level T5 (ByT5) — no tokenizer needed, operates on raw bytes
- Retrieval model only (does not generate proofs)
- Part of larger LeanDojo framework for ATP

## Update Reminder
- Check for larger LeanDojo retriever models
- Monitor kaiyuy/leandojo HF repo for updates
