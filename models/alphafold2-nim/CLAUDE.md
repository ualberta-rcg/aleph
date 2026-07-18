# AlphaFold2 NIM — Deploy/Test Notes

## Overview
NVIDIA NIM (`nvcr.io/nim/deepmind/alphafold2:2.1.1`) for protein structure prediction.

## Files
- `pvc.yaml` — RWX cache PVC (`alphafold2-nim`, **1 Ti**)
- `inferenceservice.yaml` — NIM container on port 8000, HAMi GPU slice, plus a `download-to-cache --all` init container
- `details.yaml` — v2 card with `routing.upstream_path: /predict` and `custom_params.passthrough: true`
- `test.py` — OpenAPI-driven property test battery
- `README.md` — usage example

## Database downloader
The init container `download-databases` runs the same NIM image with:

```bash
download-to-cache --all
```

This downloads the AlphaFold2 reference databases (`uniref90`, `mgnify`, `small_bfd`, `pdb70`, model params, etc.) into `/opt/nim/.cache` on the PVC before the serving container starts.

- First pull can take **4–10 hours** depending on bandwidth.
- Downloads are idempotent — if the cache already exists, the init container skips re-downloading.
- The PVC must be large enough; 1 Ti is provisioned.

## Gateway routing
The NIM's native endpoint is `POST /predict`. The card sets `routing.upstream_path: /predict`,
so the gateway forwards a public request at `/v1/biology/deepmind/alphafold2/predict` upstream as
`/predict`. `custom_params.passthrough: true` strips the OpenAI `model` and `stream` fields before forwarding.

## Test fixture
The test uses a 300-residue protein sequence and validates the response schema, required fields,
enum values, numeric ranges, and string handling by introspecting the NIM's `/openapi.json`.

## Deploy
```bash
kubectl apply -f models/alphafold2-nim/pvc.yaml
kubectl apply -f models/alphafold2-nim/inferenceservice.yaml
kubectl apply -f models/alphafold2-nim/details.yaml
```

## Test
```bash
cat models/alphafold2-nim/test.py | sudo ssh root@172.26.92.43 \
  'export PATH=$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml;
   kubectl exec -i -n models deploy/model-gateway -- python3 -'
```

## Known quirks
- First pull of the NIM image is large and slow.
- First cold start downloads the reference DBs into the PVC; keep `minReplicas: 1` until the cache is populated if you want to avoid a scale-to-zero restart during the download.
- AlphaFold2 may need a large HAMi slice or whole device depending on sequence length and MSA mode.
