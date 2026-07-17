# Mistral Small 4 (119B-2603) — Deploy/Test Notes

## Overview
NVIDIA NIM (`nvcr.io/nim/mistralai/mistral-small-4-119b-2603`) for MoE chat.

## Files
- `pvc.yaml` — RWX cache PVC (`mistral-small-4-119b-2603`, 200 Gi)
- `inferenceservice.yaml` — NIM container on port 8000, 2× L40S
- `details.yaml` — v2 chat card
- `test.py` — chat smoke test

## Deploy
```bash
kubectl apply -f models/mistral-small-4-119b-2603/pvc.yaml
kubectl apply -f models/mistral-small-4-119b-2603/inferenceservice.yaml
kubectl apply -f models/mistral-small-4-119b-2603/details.yaml
```

## Test
```bash
cat models/mistral-small-4-119b-2603/test.py | sudo ssh root@172.26.92.43 \
  'export PATH=$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml;
   kubectl exec -i -n models deploy/model-gateway -- python3 -'
```

## Known quirks
- 119B-parameter MoE; requires 2 whole L40S devices.
- First cold start is large and slow.
