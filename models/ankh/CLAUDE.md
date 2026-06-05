# Ankh Model Deployment

## What this model does
Ankh is a T5-based protein language model from ElnaggarLab (TUM). Produces embeddings for protein sequences. Requires space-separated amino acids. 113M parameters.

## Source
- **HF**: ElnaggarLab/ankh-base (https://huggingface.co/ElnaggarLab/ankh-base)
- **License**: Apache-2.0
- **Parameters**: 113M

## How the server works
- FastAPI server embedded as ConfigMap (`ankh-server`)
- Loads T5EncoderModel from HuggingFace cache
- `POST /v1/embeddings` -- accepts `input` or `sequences` (protein strings)
- Automatically spaces amino acids for T5 tokenizer
- Mean-pooled embeddings, fp16 on GPU

## Our config vs source
- venv-on-PVC pattern, torch>=2.6 with CUDA
- Pre-downloads model in init container
- GPU shared (L40S-SHARED), minReplicas: 0
- 5Gi PVC

## Deploy/update/test commands
```bash
kubectl apply -k models/ankh/
kubectl get inferenceservice ankh -n models
```

## Gateway integration
- MODEL_TYPES: `"ankh": "embedding"`
- Not in MODEL_METADATA (needs adding)
- KServe custom model (uses /v1/ prefix)

## Known Issues
- No pip version pins (torch, transformers unpinned)

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
