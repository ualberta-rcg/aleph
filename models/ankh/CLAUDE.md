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
- Mean-pooled embeddings, **fp32** on GPU (see gotcha below)

## Our config vs source
- venv-on-PVC pattern, torch>=2.6 with CUDA
- Pre-downloads model in init container
- GPU HAMi slice 8 GiB (`nvidia.com/gpumem: 8192`), minReplicas: 1 (always-on, max 3)
- PVC `ankh` (RWX, nfs-models; bare fleet naming, was `ankh-data`/`model-data`)

## Deploy/update/test commands
```bash
kubectl apply -f models/ankh/pvc.yaml
kubectl apply -f models/ankh/inferenceservice.yaml
kubectl apply -f models/ankh/details.yaml
kubectl get inferenceservice ankh -n models

# Test (external via gateway VIP + Tyk auth)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/ankh/test.py
# Or inside the gateway pod (no auth):
cat models/ankh/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

## Gateway integration
- type `embedding` (details.yaml schema v2); KServe custom model (uses /v1/ prefix).

## Known Issues / Gotchas
- **fp16 → NaN**: T5 encoders overflow to NaN in fp16. The server runs **fp32** and sanitizes
  NaN→0. Do NOT switch to fp16/half precision. (This was the FIX recorded in MODEL-STATUS.)
- No pip version pins (torch, transformers unpinned).
- Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL**.
