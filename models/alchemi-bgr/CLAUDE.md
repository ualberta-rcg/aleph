# Alchemi BGR NIM — Deploy/Test Notes

## Overview
NVIDIA NIM (`nvcr.io/nim/nvidia/alchemi-bgr:1.0.0`) for batched geometry relaxation using the MACE-MPA-O model and FIRE2 optimizer.

## Files
- `pvc.yaml` — 50 Gi RWX cache PVC
- `inferenceservice.yaml` — NIM predictor on port 8000, HAMi GPU slice
- `details.yaml` — v2 card with `custom_params.passthrough: true`
- `test.py` — OpenAPI-driven property test battery
- `README.md` — usage example

## Gateway routing
The NIM's native endpoint is `POST /v1/infer`, so the gateway forwards the public `/v1/infer` path verbatim. `custom_params.passthrough: true` strips the OpenAI `model` and `stream` fields before forwarding.

## Test fixture
An H₂ molecule in a 10 Å vacuum box is used. The test validates the response schema, health, models list, OpenAPI reachability, catalog presence, and malformed/empty-body handling.

## Deploy
```bash
kubectl apply -f models/alchemi-bgr/pvc.yaml
kubectl apply -f models/alchemi-bgr/inferenceservice.yaml
kubectl apply -f models/alchemi-bgr/details.yaml
```

## Test
```bash
cat models/alchemi-bgr/test.py | sudo ssh root@172.26.92.43 \
  'export PATH=$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml;
   KEY=$(tyk-admin.sh add-user test-alchemi-bgr default 2>/dev/null || echo "");
   kubectl exec -i -n models deploy/model-gateway -- env TYK_KEY="$KEY" GW_INSECURE=1 UPSTREAM="http://alchemi-bgr-predictor.models.svc.cluster.local" python3 -'
```

## Known quirks
- First pull of the NIM image is large and slow.
- The OpenAPI request schema uses Pydantic `anyOf` for optional fields, so the auto-driven property tests may report `SKIP` for enums/numeric ranges; the model still validates inputs correctly.
