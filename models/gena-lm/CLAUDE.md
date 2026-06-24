# GENA-LM Model Deployment

## What this model does
GENA-LM from AIRI Institute is a BERT-style DNA language model trained on T2T human genome. 110M parameters. OpenAI-compatible embeddings endpoint.

## Source
- **HF**: AIRI-Institute/gena-lm-bert-base-t2t | **License**: Apache-2.0 | **Params**: 110M

## How the server works
- `POST /v1/embeddings` -- DNA sequence(s) to mean-pooled embeddings
- Uses output_hidden_states for last-layer embeddings
- trust_remote_code=True, fp16 on GPU, max_length=512

## Our config vs source
- venv-on-PVC, torch>=2.6 CUDA, transformers<4.45
- Pre-downloads model in init container
- GPU shared (L40S-SHARED), 5Gi PVC, minReplicas: 0

## Deploy/update/test
```bash
kubectl apply -f models/gena-lm/pvc.yaml
kubectl apply -f models/gena-lm/inferenceservice.yaml
kubectl apply -f models/gena-lm/details.yaml
kubectl get inferenceservice gena-lm -n models

# Test externally via gateway VIP + Tyk auth
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/gena-lm/test.py
```

## Gateway integration
- MODEL_TYPES: `"gena-lm": "embedding"` | KServe custom | Not in MODEL_METADATA

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
