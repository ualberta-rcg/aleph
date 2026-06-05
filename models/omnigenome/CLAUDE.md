# OmniGenome Model Deployment

## What this model does
OmniGenome-186M aligns RNA sequences with secondary structures. Supports seq2str (RNA to dot-bracket), str2seq (structure to RNA), and embedding. MIT license.

## Source
- **HF**: yangheng/OmniGenome-186M | **License**: MIT | **Params**: 186M

## How the server works
- `POST /v1/embeddings` -- RNA sequence to embedding
- `POST /v1/science/predict` -- `task`: embed or seq2str
- seq2str uses transformers pipeline for text generation (experimental)
- CPU-only, no PVC

## Our config vs source
- RawDeployment mode, CPU-only
- Runtime pip install (torch CPU, ViennaRNA, transformers==4.44.2)
- No PVC -- downloads on every startup
- minReplicas: 0, maxReplicas: 1, timeout: 300s

## Deploy/update/test
```bash
kubectl apply -k models/omnigenome/
kubectl get inferenceservice omnigenome -n models
```

## Gateway integration
- MODEL_TYPES: `"omnigenome": "embedding"` | KServe custom | Not in MODEL_METADATA

## Known Issues
- No PVC means slow cold start
- seq2str is experimental (falls back to embedding on error)
- Could benefit from venv-on-PVC

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
