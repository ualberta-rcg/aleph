# OpenFold-3 — Deploy/Test Notes

## Overview
NVIDIA NIM (`nvcr.io/nim/openfold/openfold3`) for protein/DNA/RNA/ligand complex structure prediction.

## Files
- `pvc.yaml` — RWX cache PVC (`openfold-3`, 30 Gi)
- `inferenceservice.yaml` — NIM container on port 8000, HAMi GPU slice
- `details.yaml` — v2 card with `routing.strip_v1_prefix: true` and `custom_params.passthrough: true`
- `test.py` — minimal smoke test of `/v1/biology/openfold/openfold3/predict`

## Gateway routing
The NIM's native endpoint is `/biology/openfold/openfold3/predict` (no `/v1`). The card sets
`routing.strip_v1_prefix: true`, so the gateway forwards a public request at
`/v1/biology/openfold/openfold3/predict` upstream as `/biology/openfold/openfold3/predict`.
`custom_params.passthrough: true` strips the OpenAI `model` and `stream` fields before forwarding.

## Input quirks
- Protein sequences must be accompanied by a non-empty MSA. The smoke test provides the query
  sequence itself as a CSV MSA: `key,sequence\n-1,<QUERY>`.
- The response shape is `{"outputs": [{"input_id": ..., "structures_with_scores": [{"structure": "data_...", "confidence_score": 0.0-1.0, ...}]}]}`.

## Deploy
```bash
kubectl apply -f models/openfold-3/pvc.yaml
kubectl apply -f models/openfold-3/inferenceservice.yaml
kubectl apply -f models/openfold-3/details.yaml
```

## Test
```bash
cat models/openfold-3/test.py | sudo ssh root@172.26.92.43 \
  'export PATH=$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml;
   kubectl exec -i -n models deploy/model-gateway -- python3 -'
```

## Known quirks
- First pull of the NIM image is large and slow.
- Inference is diffusion-based; even the smoke test uses one sample.
