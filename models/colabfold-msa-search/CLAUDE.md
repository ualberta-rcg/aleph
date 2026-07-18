# colabfold-msa-search

Operational notes for the ColabFold MSA Search NIM on Aleph cluster 43.

## Image

`nvcr.io/nim/colabfold/msa-search:2.5.0`

## Deploy path

```bash
kubectl apply -f models/colabfold-msa-search/pvc.yaml
kubectl apply -f models/colabfold-msa-search/inferenceservice.yaml
kubectl apply -f models/colabfold-msa-search/details.yaml
```

## Why these choices

- 24 GiB vGPU (`nvidia.com/gpumem: "24576"`) fits inside a single L40S slice
  while leaving headroom for MMseqs2 GPU search buffers.
- 100 Gi PVC holds downloaded databases and avoids re-download on every cold
  start.
- `/dev/shm` 16 Gi emptyDir prevents MMseqs2 temp-file pressure in the
  container rootfs.

## Gateway card flags

- `routing.strip_v1_prefix: true` — public endpoint has `/v1/` but NIM native
  endpoint does not.
- `custom_params.passthrough: true` — strip OpenAI-style `model`/`stream` from
  upstream body.

## Test command

```bash
cat models/colabfold-msa-search/test.py | \
  kubectl exec -i -n models deploy/model-gateway -- python3 -
```

Set `GW_INSECURE=1` when running against the cluster self-signed edge cert.

## Cold start

Expect 2–5 minutes on first pull while the image and databases land. The
startup probe allows up to 30 minutes.

## Scale-to-zero

`minReplicas: 0`; idle retention is 15 minutes. After testing, verify no pods
remain:

```bash
kubectl get pods -n models -l serving.kserve.io/inferenceservice=colabfold-msa-search
```

## Troubleshooting

- If scheduling fails with `CardInsufficientMemory`, free vGPU memory by
  scaling other warm models to zero first.
- If the NIM returns 404 on the native endpoint, confirm the gateway is
  running a build that supports `routing.strip_v1_prefix`.

## Status

See `models/MODEL-STATUS.md` for the latest verified test tally.
