# bge-small Notes

## Purpose
Small/always-on English text embedding service (384-dim) for fast short-text retrieval.
Template-C (`type: embedding`) — TEI-fetched-model variant (no PVC).

## Runtime
- Image: `ghcr.io/huggingface/text-embeddings-inference:cpu-latest`
- Entry args: `--model-id=BAAI/bge-small-en-v1.5 --port=8080 --dtype=float32`
- API path(s): `POST /v1/embeddings` (OpenAI-shaped), `GET /health`
- TEI downloads the ~130MB public model itself on pod start (no init container, no PVC).

## Resources
- CPU request/limit: 2/4
- Memory request/limit: 4Gi/8Gi
- GPU request: **none** (CPU-only)

## Storage
- PVC name: **none** (model is small + public; TEI fetches it into the container HF cache on start)
- Trade-off: every cold start re-downloads ~130MB (acceptable for an always-on, small model).

## Known quirks
- **Model echo is `BAAI/bge-small-en-v1.5`:** TEI echoes the `--model-id`. Harmless; the gateway
  catalog lists it as `bge-small`.
- **No HF_TOKEN in the ISVC** — the model is public, so TEI doesn't need it. (If a model is ever
  gated, add the `hf-token` secret env + a PVC/init-container like bge-m3.)
- **English only** (use bge-m3 for multilingual).
- No query instruction prefix (BGE v1.5 convention).
- Truncation to 512 tokens is safe (tiny model, CPU).

## Deploy / update steps
1. `kubectl apply -f inferenceservice.yaml` (TEI cpu-latest, minReplicas 1).
2. `kubectl apply -f details.yaml` (Template-C card; hot-reloads via ConfigMap watch).
> Apply method: to sync the card only, apply `details.yaml` alone — don't re-apply the ISVC with
> plain client-side `kubectl apply` (churns a Knative revision).

## Validation checks
- [x] basic request — dim == 384
- [x] batch (3 texts → 3 vectors, same dim)
- [x] usage + model echo (BAAI/bge-small-en-v1.5)
- [x] distinctness (cos 0.53)
- [x] encoding_format float + base64
- [x] truncation (>512 tokens → 384-dim, no 500)
- [x] guardrails (chat→embed 404, unknown model 404)
- [x] catalog entry (type=embedding, ctx 512)
- [x] no secret values in manifest (public model; no HF_TOKEN used)
