# RFdiffusion — Deploy/Test Notes

## Overview
NVIDIA NIM (`nvcr.io/nim/ipd/rfdiffusion`) for protein backbone design / binder generation.

## Files
- `pvc.yaml` — RWX cache PVC (`rfdiffusion`, 50 Gi)
- `inferenceservice.yaml` — NIM container on port 8000, HAMi GPU slice
- `details.yaml` — v2 card with `routing.strip_v1_prefix: true` and `custom_params.passthrough: true`
- `test.py` — minimal smoke test of `/v1/biology/ipd/rfdiffusion/generate`

## Gateway routing
The NIM's native endpoint is `/biology/ipd/rfdiffusion/generate` (no `/v1`). The card sets
`routing.strip_v1_prefix: true`, so the gateway forwards a public request at
`/v1/biology/ipd/rfdiffusion/generate` upstream as `/biology/ipd/rfdiffusion/generate`.
`custom_params.passthrough: true` strips the OpenAI `model` and `stream` fields before forwarding.

## Test fixture
The smoke test fetches the first 200 ATOM lines of PDB `1R42` from RCSB and asks RFdiffusion to
keep residues A19-42 while generating 5-10 new residues.

## Deploy
```bash
kubectl apply -f models/rfdiffusion/pvc.yaml
kubectl apply -f models/rfdiffusion/inferenceservice.yaml
kubectl apply -f models/rfdiffusion/details.yaml
```

## Test
```bash
cat models/rfdiffusion/test.py | sudo ssh root@172.26.92.43 \
  'export PATH=$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml;
   kubectl exec -i -n models deploy/model-gateway -- python3 -'
```

## Known quirks
- First pull of the NIM image is large and slow.
- The smoke test uses only 5 diffusion steps for speed and a small input structure to fit the
  default preallocated scratch budget.
