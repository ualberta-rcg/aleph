# ProteinMPNN NIM — Deploy/Test Notes

## Overview
NVIDIA NIM (`nvcr.io/nim/ipd/proteinmpnn:1.1.0`) for designing protein sequences from backbone structures.

## Files
- `pvc.yaml` — 50 Gi RWX cache PVC
- `inferenceservice.yaml` — NIM predictor on port 8000, HAMi GPU slice
- `details.yaml` — v2 card with `routing.strip_v1_prefix: true` and `custom_params.passthrough: true`
- `test.py` — OpenAPI-driven property test battery
- `README.md` — usage example

## Gateway routing
The NIM's native endpoint is `POST /biology/ipd/proteinmpnn/predict`. The card sets `routing.strip_v1_prefix: true`, so the gateway forwards a public request at `/v1/biology/ipd/proteinmpnn/predict` upstream as `/biology/ipd/proteinmpnn/predict`. `custom_params.passthrough: true` strips the OpenAI `model` and `stream` fields before forwarding.

## Test fixture
A minimal 2-residue glycine backbone PDB is used as the design target. The test validates the response schema, health, models list, OpenAPI reachability, catalog presence, and malformed/empty-body handling. Required-field, enum, numeric-range, and string-format checks are driven from `/openapi.json`.

## Deploy
```bash
kubectl apply -f models/proteinmpnn-nim/pvc.yaml
kubectl apply -f models/proteinmpnn-nim/inferenceservice.yaml
kubectl apply -f models/proteinmpnn-nim/details.yaml
```

## Test
```bash
cat models/proteinmpnn-nim/test.py | sudo ssh root@172.26.92.43 \
  'export PATH=$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml;
   KEY=$(tyk-admin.sh add-user test-proteinmpnn default 2>/dev/null || echo "");
   kubectl exec -i -n models deploy/model-gateway -- env TYK_KEY="$KEY" GW_INSECURE=1 UPSTREAM="http://proteinmpnn-nim-predictor.models.svc.cluster.local" python3 -'
```

## Known quirks
- First pull of the NIM image is large and slow.
- The OpenAPI request schema uses Pydantic `anyOf` for optional fields, so the auto-driven property tests may report `SKIP` for enums/numeric ranges; the model still validates inputs correctly.
