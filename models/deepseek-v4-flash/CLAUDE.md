# DeepSeek-V4-Flash — Deploy/Test Notes

## Overview
NVIDIA NIM (`nvcr.io/nim/deepseek-ai/deepseek-v4-flash`) for MoE chat.

## Files
- `pvc.yaml` — RWX cache PVC (`deepseek-v4-flash`, 200 Gi)
- `inferenceservice.yaml` — NIM container on port 8000, 4× L40S
- `details.yaml` — v2 chat card
- `test.py` — chat smoke test

## Deploy
```bash
kubectl apply -f models/deepseek-v4-flash/pvc.yaml
kubectl apply -f models/deepseek-v4-flash/inferenceservice.yaml
kubectl apply -f models/deepseek-v4-flash/details.yaml
```

## Test
```bash
cat models/deepseek-v4-flash/test.py | sudo ssh root@172.26.92.43 \
  'export PATH=$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml;
   kubectl exec -i -n models deploy/model-gateway -- python3 -'
```

## Known quirks
- 284B-parameter FP8 model; requires 4 whole L40S devices.
- First cold start is large and slow.
