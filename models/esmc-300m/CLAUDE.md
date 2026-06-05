# ESM-C 300M Model Deployment

## What this model does
ESM-C (Cambrian) 300M from EvolutionaryScale (Meta spinoff). Next-gen protein LM, drop-in replacement for ESM-2 with improved performance. Uses esm SDK.

## Source
- **HF**: EvolutionaryScale/esmc-300m-2024-12 | **License**: MIT | **Params**: 300M

## How the server works
- `POST /v1/embeddings` -- protein sequence(s) to embeddings
- Uses esm SDK: ESMC.from_pretrained -> encode -> logits with return_embeddings
- Mean pool across sequence dimension

## Our config vs source
- venv-on-PVC with esm package, torch>=2.6 CUDA
- HF_TOKEN required for download
- GPU shared (L40S-SHARED), 5Gi PVC, minReplicas: 0

## Deploy/update/test
```bash
kubectl apply -k models/esmc-300m/
kubectl get inferenceservice esmc-300m -n models
```

## Gateway integration
- MODEL_TYPES: `"esmc-300m": "embedding"` | KServe custom | Not in MODEL_METADATA

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
