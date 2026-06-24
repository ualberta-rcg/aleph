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
kubectl apply -f models/esmc-300m/pvc.yaml
kubectl apply -f models/esmc-300m/inferenceservice.yaml
kubectl apply -f models/esmc-300m/details.yaml
kubectl get inferenceservice esmc-300m -n models

# Test externally via gateway VIP + Tyk auth
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/esmc-300m/test.py
```

## Gateway integration
- MODEL_TYPES: `"esmc-300m": "embedding"` | KServe custom | Not in MODEL_METADATA

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked

## Embeddings pass (2026-06-19)
- Card rewritten to v2 Template C; **PVC migrated RWO→RWX** (recreated nfs-models RWX; reclaim=Delete
  → one-time re-download). ESM-C's cold rebuild (esm SDK venv + ~1.2GB model) is **slow (>6 min)** —
  the test's 6-min wake window timed out once; re-ran after the pod was Ready → all green.
- 10-check battery via the gateway: **8 PASS / 2 EXP / 0 FAIL** (dim 960, ctx 2048). Run:
  `cat models/esmc-300m/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -`.
- Deploy with `kubectl apply -f` (pvc.yaml / inferenceservice.yaml / details.yaml), not `-k`.
