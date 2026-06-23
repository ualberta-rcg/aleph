# bge-m3 Notes

## Purpose
Always-on multilingual text embedding service (dense `/v1/embeddings`) for retrieval/RAG.
Template-C (`type: embedding`) exemplar for the embeddings pass.

## Runtime
- Image: `ghcr.io/huggingface/text-embeddings-inference:cpu-1.6`
- Entry args: `--model-id=/data --port=8080 --dtype=float32`
- API path(s): `POST /v1/embeddings` (OpenAI-shaped), `GET /health`

## Resources
- CPU request/limit: init 2/4, server 4/8
- Memory request/limit: init 4Gi/8Gi, server 8Gi/**16Gi** (bumped from 8Gi 2026-06-19 — see below)
- GPU request: **none** (CPU-only; no HAMi slice, no gpu nodeSelector)

## Storage
- PVC name: `bge-m3-data` (ReadWriteMany, nfs-models, 5Gi)
- Mount path: `/data` (init writes, server reads readOnly)
- Warm-cache condition: `if [ -f /data/config.json ]` → skip download

## Known quirks
- **Model echo is `/data`:** TEI echoes the `--model-id` (`/data`), not `bge-m3`. Harmless; the
  gateway catalog still lists it as `bge-m3`. (To change, set `--model-id=bge-m3` in the ISVC —
  a service tweak, out of scope for this pass.)
- **Oversize single input — resolved (memory bumped to 16Gi):** a single input over the 8192-token
  limit used to OOMKill the pod (exitCode 137) — the fp32 XLM-R forward pass over ~8k tokens spiked
  past the 8Gi limit. Bumped the server container limit 8Gi→16Gi (2026-06-19); the truncation test
  now passes (prompt_tokens=8003 → 1024-dim vector, no OOM).
- **Always-on by design:** `minReplicas: 1`, no scale-to-zero (TEI cold-start avoided). Leave it
  running; do not add `serving.kserve.io/stop=true`.
- No query instruction prefix needed (unlike BGE v1.5).

## Deploy / update steps
1. `kubectl apply -f pvc.yaml` (RWX weights; skips re-download when present).
2. `kubectl apply -f inferenceservice.yaml` (TEI cpu-1.6, minReplicas 1).
3. `kubectl apply -f details.yaml` (Template-C card; hot-reloads via ConfigMap watch).

## Validation checks
- [x] basic request — dim == 1024
- [x] batch (3 inputs → 3 vectors, same dim)
- [x] usage (prompt_tokens) + model echo
- [x] encoding_format float + base64
- [x] multilingual input
- [x] guardrails (chat→embed 404, unknown model 404)
- [x] catalog entry (type=embedding, ctx 8192)
- [x] truncation (>8192 tokens → 1024-dim, no OOM @ 16Gi)
- [x] no secret values in manifest (HF_TOKEN via hf-token Secret)
