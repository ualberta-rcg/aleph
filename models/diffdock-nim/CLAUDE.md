# DiffDock NIM — Deploy/Test Notes

## Overview
NVIDIA NIM (`nvcr.io/nim/mit/diffdock:2.3`) for generative molecular blind docking.

## Files
- `pvc.yaml` — 100 Gi RWX cache PVC
- `inferenceservice.yaml` — NIM predictor on port 8000, HAMi GPU slice
- `details.yaml` — v2 card with `routing.strip_v1_prefix: true` and `custom_params.passthrough: true`
- `test.py` — OpenAPI-driven property test battery
- `README.md` — usage example

## Gateway routing
The NIM's native endpoint is `POST /molecular-docking/diffdock/generate`. The card sets `routing.strip_v1_prefix: true`, so the gateway forwards a public request at `/v1/molecular-docking/diffdock/generate` upstream as `/molecular-docking/diffdock/generate`. `custom_params.passthrough: true` strips the OpenAI `model` and `stream` fields before forwarding.

## Test fixture
A minimal 2-residue glycine backbone PDB is used as the protein, with ethanol (`CCO`) as the SMILES ligand. The test validates the response schema, health, models list, OpenAPI reachability, catalog presence, and malformed/empty-body handling.

## Deploy
```bash
kubectl apply -f models/diffdock-nim/pvc.yaml
kubectl apply -f models/diffdock-nim/inferenceservice.yaml
kubectl apply -f models/diffdock-nim/details.yaml
```

## Test
```bash
cat models/diffdock-nim/test.py | sudo ssh root@172.26.92.43 \
  'export PATH=$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml;
   KEY=$(tyk-admin.sh add-user test-diffdock default 2>/dev/null || echo "");
   kubectl exec -i -n models deploy/model-gateway -- env TYK_KEY="$KEY" GW_INSECURE=1 UPSTREAM="http://diffdock-nim-predictor.models.svc.cluster.local" python3 -'
```

## Known quirks
- First pull of the NIM image is large and slow.
- The OpenAPI request schema uses Pydantic `anyOf` for optional fields, so the auto-driven property tests may report `SKIP` for enums/numeric ranges; the model still validates inputs correctly.
- Fast test runs use `steps: 2` and `num_poses: 1` to keep runtime short.
