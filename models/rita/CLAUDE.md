# RITA-XL Model Deployment

## What this model does
RITA-XL from LightOn is a 1.2B parameter autoregressive protein language model. Generates novel protein sequences from a prefix prompt. CPU-only (large model).

## Source
- **HF**: lightonai/RITA_xl | **License**: Apache-2.0 | **Params**: 1.2B

## How the server works
- `POST /v1/generate` -- accepts `prompt` (amino acid prefix), `max_length`, `num_sequences`, `temperature`
- Uses AutoModelForCausalLM for autoregressive generation
- float32 (no fp16 — CPU only)

## Our config vs source
- venv-on-PVC (venv2 to avoid stale cache), transformers<4.38
- CPU-only, 16Gi/32Gi memory, 8/16 CPU cores
- 10Gi PVC, minReplicas: 0, timeout: 300s
- Model downloads via snapshot_download

## Deploy/update/test
```bash
kubectl apply -k models/rita/
kubectl get inferenceservice rita -n models
```

## Gateway integration
- MODEL_TYPES: `"rita": "embedding"` | KServe custom | Not in MODEL_METADATA
- Note: gateway type is "embedding" but model generates sequences

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
