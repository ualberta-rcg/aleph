# esm2-35m Notes

## Purpose
Smallest ESM-2 protein-embedding service (480-dim mean-pooled) — fastest variant.
Template-C (`type: embedding`), custom-transformers-on-GPU.

## Runtime
- Image: `python:3.11-slim` running `/data/venv/bin/python /app/server.py` (cu121 torch + transformers 4.46.3)
- server.py: embedded as the `esm2-35m-server` ConfigMap; EsmModel, loads from HF hub (cache on PVC)
- API: `POST /v1/embeddings` (OpenAI-shaped; `input`/`sequences`), `GET /health`

## Resources
- CPU/Mem: init 2/4Gi, server 2/4Gi
- GPU: HAMi `nvidia.com/gpumem: 3072` (3 GiB slice, fp16)

## Storage
- PVC `esm2-35m-data` (**ReadWriteMany**, nfs-client, 15Gi) — split out of inferenceservice.yaml 2026-06-19.
- Mount `/data` (venv + HF cache via `HF_HOME=/data/hf_cache`); server code at `/app` (ConfigMap).

## Known quirks
- Loads model from HF hub (`facebook/esm2_t12_35M_UR50D`), cached on PVC (not a snapshot dir).
- 480-dim (smallest ESM-2), mean-pooled over residues, max 1024.
- usage: residue count. Scale-to-zero (`minReplicas: 0`).

## Deploy / update steps
1. `kubectl apply -f pvc.yaml` (RWX).
2. `kubectl apply -f inferenceservice.yaml` (ConfigMap server.py + ISVC).
3. `kubectl apply -f details.yaml` (Template-C card).

## Validation checks
- [x] dim == 480, batch, model-echo, usage, distinctness, encoding_format, truncation, guardrails, catalog
- [x] no secret values in manifest
