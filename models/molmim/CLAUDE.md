# MolMIM — Deploy/Test Notes

## Overview
NVIDIA NIM (`nvcr.io/nim/nvidia/molmim`) for generative molecular design.

## Files
- `pvc.yaml` — RWX cache PVC (`molmim`, 30 Gi)
- `inferenceservice.yaml` — NIM container on port 8000, HAMi GPU slice
- `details.yaml` — v2 card with `routing.strip_v1_prefix: true` and `custom_params.passthrough: true`
- `test.py` — minimal smoke test of `/v1/biology/nvidia/molmim/generate`

## Gateway routing
The NIM's native endpoint is `/biology/nvidia/molmim/generate` (no `/v1`). The card sets
`routing.strip_v1_prefix: true`, so the gateway forwards a public request at
`/v1/biology/nvidia/molmim/generate` upstream as `/biology/nvidia/molmim/generate`.
`custom_params.passthrough: true` strips the OpenAI `model` and `stream` fields before forwarding.

## Test fixture
The smoke test uses aspirin (`CC(=O)Oc1ccccc1C(=O)O`) as the seed SMILES and asks for 3
molecules with only 1 CMA-ES iteration for speed.

## Deploy
```bash
kubectl apply -f models/molmim/pvc.yaml
kubectl apply -f models/molmim/inferenceservice.yaml
kubectl apply -f models/molmim/details.yaml
```

## Test
```bash
cat models/molmim/test.py | sudo ssh root@172.26.92.43 \
  'export PATH=$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml;
   kubectl exec -i -n models deploy/model-gateway -- python3 -'
```

## Known quirks
- First pull of the NIM image is large and slow.
- The smoke test reduces `particles` and `iterations` for speed.
