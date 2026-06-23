# esm1b Notes

## Purpose
Protein-sequence embedding service (1280-dim mean-pooled) for proteomics downstream tasks.
Template-C (`type: embedding`) — custom-transformers-server-on-GPU variant.

## Runtime
- Image: `python:3.11-slim` running `/data/venv/bin/python /app/server.py` (torch>=2.6 cu126 + transformers)
- server.py: embedded as the `esm1b-server` ConfigMap (mounted at `/app`); loads the model from the HF hub (cache on PVC)
- API path(s): `POST /v1/embeddings` (OpenAI-shaped; accepts `input` or `sequences`), `GET /health`

## Resources
- CPU request/limit: init 2/4, server 2/4
- Memory request/limit: init 4Gi/8Gi, server 4Gi/8Gi
- GPU request: `nvidia.com/gpu: 1` · HAMi `nvidia.com/gpumem: 10240` (10 GiB slice; fp16)

## Storage
- PVC name: `esm1b-data` (**ReadWriteMany**, nfs-models, 5Gi) — migrated RWO→RWX 2026-06-19
  (was bound RWO, which capped the ISVC's `scaleTarget: 5` at 1 pod; recreated RWX).
- Mount path: `/data` (venv + HF cache via `HF_HOME=/data/hf_cache`); app at `/app` (ConfigMap).

## Known quirks
- **PVC migrated RWO→RWX (2026-06-19):** the PVC was bound ReadWriteOnce (immutable → required
  delete+recreate; reclaim=Delete triggered a one-time ~2.5GB model re-download on next cold start).
  Now RWX, so `scaleTarget: 5` works.
- **Loads model from HF hub** (not a snapshot on PVC) — `HF_HOME=/data/hf_cache` caches it. Init pre-downloads.
- **Predecessor to ESM-2** (esm2-650m); 1280-dim, max 1024 residues, mean-pooled, fp16 on GPU.
- usage: `prompt_tokens`/`total_tokens` = residue count.
- **v2 card conversion (2026-06-19):** old-schema card rewritten to v2 Template C.

## Deploy / update steps
1. `kubectl apply -f pvc.yaml` — **NOTE:** will FAIL until the RWO PVC is recreated (see file header).
2. `kubectl apply -f inferenceservice.yaml` (ConfigMap server.py + ISVC).
3. `kubectl apply -f details.yaml` (Template-C card; hot-reloads via ConfigMap watch).
> Apply method: to sync the card only, apply `details.yaml` alone — don't re-apply the ISVC with plain
> client-side `kubectl apply` (churns a Knative revision).

## Validation checks
- [x] basic request — dim == 1280
- [x] batch (3 seqs → 3 vectors, same dim)
- [x] usage + model echo (esm1b)
- [x] distinctness (cos 0.95)
- [x] encoding_format=float
- [x] truncation (>1024 residues → 1280-dim, no 500)
- [x] guardrails (chat→embed 404, unknown model 404)
- [x] catalog entry (type=embedding, ctx 1024)
- [x] no secret values in manifest
