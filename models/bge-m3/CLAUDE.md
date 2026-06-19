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
- Memory request/limit: init 4Gi/8Gi, server 6Gi/**8Gi** ← see OOM caveat
- GPU request: **none** (CPU-only; no HAMi slice, no gpu nodeSelector)

## Storage
- PVC name: `bge-m3-data` (ReadWriteMany, nfs-client, 5Gi)
- Mount path: `/data` (init writes, server reads readOnly)
- Warm-cache condition: `if [ -f /data/config.json ]` → skip download

## Known quirks
- **Model echo is `/data`:** TEI echoes the `--model-id` (`/data`), not `bge-m3`. Harmless; the
  gateway catalog still lists it as `bge-m3`. (To change, set `--model-id=bge-m3` in the ISVC —
  a service tweak, out of scope for this pass.)
- **Oversize single input → OOMKill:** a single input well over the 8192-token limit
  (exitCode 137, reason OOMKilled) spikes the fp32 XLM-R forward pass past the 8Gi memory limit,
  restarting the pod and cascading 502s. TEI truncates per-sequence by default, but the ~8k-token
  activation still exceeds 8Gi. The test suite intentionally **skips** this (truncation check).
  Mitigation if needed: raise the container memory limit (service change) or pre-truncate client-side.
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
- [~] truncation — SKIPPED (OOM caveat above)
- [x] no secret values in manifest (HF_TOKEN via hf-token Secret)
