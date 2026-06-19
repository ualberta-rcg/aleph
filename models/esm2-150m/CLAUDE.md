# esm2-150m Notes

## Purpose
Protein-sequence embedding service (640-dim mean-pooled) — the mid-size ESM-2 variant
(speed/accuracy balance). Template-C (`type: embedding`), custom-transformers-on-GPU.

## Runtime
- Image: `python:3.11-slim` running `/data/venv/bin/python /app/server.py` (torch + transformers, EsmModel)
- server.py: embedded as the `esm2-150m-server` ConfigMap (mounted at `/app`)
- API path(s): `POST /v1/embeddings` (OpenAI-shaped; `input`/`sequences`), `GET /health`
- GPU: HAMi sub-GPU slice, fp16; max_length=1024

## Storage
- PVC name: `esm2-150m-data` (**ReadWriteMany**, nfs-models, 5Gi) — **migrated RWO→RWX 2026-06-19**
  (was bound RWO; recreated; reclaim=Delete triggered a one-time ~600MB re-download, validated).
- Mount path: `/data` (venv + model). App at `/app` (ConfigMap).

## Known quirks
- **PVC migrated RWO→RWX (2026-06-19):** was ReadWriteOnce (immutable → delete+recreate).
- ESM-2 150M → **640-dim** embeddings, mean-pooled over residues (not 1280 like the 650M variant).
- usage: `prompt_tokens`/`total_tokens` = residue count.
- **Scale-to-zero** (`minReplicas: 0`): cold start ~1–2 min (rebuild after PVC recreate).
- **v2 card conversion (2026-06-19):** old-schema card rewritten to v2 Template C.

## Deploy / update steps
1. `kubectl apply -f pvc.yaml` (RWX; caches venv + model).
2. `kubectl apply -f inferenceservice.yaml` (ConfigMap server.py + ISVC).
3. `kubectl apply -f details.yaml` (Template-C card; hot-reloads via ConfigMap watch).
> Apply method: to sync the card/PVC only, apply `details.yaml`/`pvc.yaml` alone — don't re-apply the
> ISVC with plain client-side `kubectl apply` (churns a Knative revision).

## Validation checks
- [x] basic request — dim == 640
- [x] batch (3 seqs → 3 vectors, same dim)
- [x] usage + model echo (esm2-150m)
- [x] distinctness (cos 0.81)
- [x] encoding_format=float
- [x] truncation (>1024 residues → 640-dim, no 500)
- [x] guardrails (chat→embed 404, unknown model 404)
- [x] catalog entry (type=embedding, ctx 1024)
- [x] no secret values in manifest
