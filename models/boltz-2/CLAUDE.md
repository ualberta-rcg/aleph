# Boltz-2 — Deploy/Test Notes

## Overview
NVIDIA NIM (`nvcr.io/nim/mit/boltz2`) for protein/DNA/RNA/ligand structure prediction.

## Files
- `pvc.yaml` — RWX cache PVC (`boltz-2`, 30 Gi)
- `inferenceservice.yaml` — NIM container on port 8000, HAMi GPU slice
- `details.yaml` — v2 card with `routing.strip_v1_prefix: true`
- `test.py` — minimal smoke test of `/v1/biology/mit/boltz2/predict`

## Gateway routing
The NIM's native endpoint is `/biology/mit/boltz2/predict` (no `/v1`). The card sets
`routing.strip_v1_prefix: true`, so the gateway forwards a public request at
`/v1/biology/mit/boltz2/predict` upstream as `/biology/mit/boltz2/predict`.

## Startup patch
The container command checks `/opt/nim/lib/boltz_assist/boltz_pipeline.py` for a
`confidence_score` KeyError (NIM v1.7.0) and patches it idempotently before starting
the server.

## Deploy
```bash
kubectl apply -f models/boltz-2/pvc.yaml
kubectl apply -f models/boltz-2/inferenceservice.yaml
kubectl apply -f models/boltz-2/details.yaml
```

## Test
```bash
cat models/boltz-2/test.py | sudo ssh root@172.26.92.43 \
  'export PATH=$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml;
   kubectl exec -i -n models deploy/model-gateway -- python3 -'
```

## Known quirks
- First pull of the NIM image is large and slow.
- Inference is diffusion-based; even the smoke test uses reduced sampling steps.
