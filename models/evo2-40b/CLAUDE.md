# Evo2-40b — Deploy/Test Notes

## Overview
NVIDIA NIM (`nvcr.io/nim/arc/evo2-40b`) for Arc Institute Evo2 40B genome modeling.

## Files
- `pvc.yaml` — RWX cache PVC (`evo2-40b`, 150 Gi)
- `inferenceservice.yaml` — NIM container on port 8000, 1× L40S HAMi vGPU slice
- `details.yaml` — v2 science card (`strip_v1_prefix`, `passthrough`)
- `test.py` — science smoke test

## Deploy
```bash
kubectl apply -f models/evo2-40b/pvc.yaml
kubectl apply -f models/evo2-40b/inferenceservice.yaml
kubectl apply -f models/evo2-40b/details.yaml
```

## Test
```bash
cat models/evo2-40b/test.py | sudo ssh root@172.26.92.43 \
  'export PATH=$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml;
   kubectl exec -i -n models deploy/model-gateway -- python3 -'
```

## Known quirks
- Native endpoint `/biology/arc/evo2/generate` lacks `/v1`; gateway strips the prefix.
- Evo2 40B uses FP8 Transformer Engine and may prefer Hopper/H100; L40S compatibility is TBD.
- First cold start is large and slow.
