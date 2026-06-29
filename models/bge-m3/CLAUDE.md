# bge-m3 Notes

## Purpose
Always-on multilingual text embedding service (dense `/v1/embeddings`) for retrieval/RAG.
Template-C (`type: embedding`) exemplar for the embeddings pass.

## Runtime
- Image: `ghcr.io/huggingface/text-embeddings-inference:89-1.9` (CUDA build for Ada / SM 8.9 / L40S)
- Entry args: `--model-id=/data --port=8080 --dtype=float16`
- API path(s): `POST /v1/embeddings` (OpenAI-shaped), `GET /health`

## Resources
- CPU request/limit: init 2/4, server 2/4
- Memory request/limit: init 4Gi/8Gi, server 4Gi/8Gi
- GPU request: **HAMi vGPU slice** — `nvidia.com/gpu: "1"` + `nvidia.com/gpumem: "8192"`; `nodeSelector gpu=on`. Uses ~1.6 GB VRAM (fp16), so it shares one L40S with other tenants.

## Storage
- PVC name: `bge-m3-data` (ReadWriteMany, nfs-models, 5Gi)
- Mount path: `/data` (init writes, server reads readOnly)
- Warm-cache condition: `if [ -f /data/config.json ]` → skip download

## Known quirks
- **Model echo is `/data`:** TEI echoes the `--model-id` (`/data`), not `bge-m3`. Harmless; the
  gateway catalog still lists it as `bge-m3`. (To change, set `--model-id=bge-m3` in the ISVC —
  a service tweak, out of scope for this pass.)
- **Oversize single input:** on the old CPU path a single input over the 8192-token limit could
  OOMKill the pod (the fp32 XLM-R forward pass over ~8k tokens spiked past the 8Gi limit). On GPU
  (fp16) the forward pass runs in VRAM, so host memory is no longer the bottleneck; the truncation
  test passes (prompt_tokens=8003 → 1024-dim vector).
- **Migrated CPU→GPU (2026-06-28):** was TEI `cpu-1.6` / fp32. Now `89-1.9` (CUDA/Ada) / fp16 on a
  HAMi slice. Clean delete+redeploy (PVC reused). Gateway 9/2/0; batch-32 embed ~183 ms/req.
- **Always-on by design:** `minReplicas: 1`, no scale-to-zero (TEI cold-start avoided). Leave it
  running; do not add `serving.kserve.io/stop=true`.
- No query instruction prefix needed (unlike BGE v1.5).

## Deploy / update steps
1. `kubectl apply -f pvc.yaml` (RWX weights; skips re-download when present).
2. `kubectl apply -f inferenceservice.yaml` (TEI 89-1.9 CUDA, fp16, HAMi slice, minReplicas 1).
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
