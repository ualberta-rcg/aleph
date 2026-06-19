# nucleotide-transformer Notes

## Purpose
DNA-sequence embedding service (1024-dim mean-pooled) — InstaDeepAI NT v2 500M multi-species.
Template-C (`type: embedding`), custom-transformers-on-GPU.

## Runtime
- Image: `python:3.11-slim` running `/data/venv/bin/python /app/server.py` (cu121 torch + transformers<4.45)
- server.py: `nucleotide-transformer-server` ConfigMap; EsmModel, trust_remote_code
- API: `POST /v1/embeddings` (OpenAI-shaped; `input`/`sequences`), `GET /health`

## Resources
- CPU/Mem: init 2/4Gi, server 2/4Gi
- GPU: HAMi `nvidia.com/gpumem: 4096`

## Storage
- PVC `nucleotide-transformer-data` (**ReadWriteMany**, nfs-models, 15Gi) — split out of inferenceservice.yaml 2026-06-19.
  NOTE: live PVC is on `nfs-models`; repo ISVC said `nfs-client` (SC immutable — matched live).
- Mount `/data` (venv + HF cache); app at `/app` (ConfigMap).

## Known quirks
- `ignore_mismatched_sizes=True` on load; transformers pinned <4.45.
- Server already OpenAI-compliant (batch + usage + mean-pool).
- usage: residue count. Scale-to-zero (`minReplicas: 0`).

## Deploy / update steps
1. `kubectl apply -f pvc.yaml` (RWX).
2. `kubectl apply -f inferenceservice.yaml` (ConfigMap server.py + ISVC).
3. `kubectl apply -f details.yaml` (Template-C card).

## Validation checks
- [x] dim == 1024, batch, model-echo, usage, distinctness, truncation, guardrails, catalog
- [x] no secret values in manifest
