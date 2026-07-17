# GenMol — Deploy/Test Notes

## Overview
NVIDIA NIM (`nvcr.io/nim/nvidia/genmol-generate`) for generative molecular design.

## Files
- `pvc.yaml` — RWX cache PVC (`genmol`, 30 Gi)
- `inferenceservice.yaml` — NIM container on port 8000, HAMi GPU slice
- `details.yaml` — v2 card with `routing.strip_v1_prefix: true` and `custom_params.passthrough: true`
- `test.py` — minimal smoke test of `/v1/biology/nvidia/genmol/generate`

## Gateway routing
The NIM's native endpoint is `/biology/nvidia/genmol/generate` (no `/v1`). The card sets
`routing.strip_v1_prefix: true`, so the gateway forwards a public request at
`/v1/biology/nvidia/genmol/generate` upstream as `/biology/nvidia/genmol/generate`.
`custom_params.passthrough: true` strips the OpenAI `model` and `stream` fields before forwarding.

## Test fixture
The smoke test uses aspirin (`CC(=O)Oc1ccccc1C(=O)O`) as the seed SMILES and asks for 3 molecules.

## Deploy
```bash
kubectl apply -f models/genmol/pvc.yaml
kubectl apply -f models/genmol/inferenceservice.yaml
kubectl apply -f models/genmol/details.yaml
```

## Test
```bash
cat models/genmol/test.py | sudo ssh root@172.26.92.43 \
  'export PATH=$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml;
   kubectl exec -i -n models deploy/model-gateway -- python3 -'
```

## Known quirks
- First pull of the NIM image is large and slow.
- The smoke test keeps `num_molecules` small for speed.
