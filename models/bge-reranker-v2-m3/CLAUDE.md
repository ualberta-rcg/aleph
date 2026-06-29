# bge-reranker-v2-m3 Notes

## Purpose
Always-on multilingual cross-encoder reranker (`/v1/rerank`) for second-stage RAG re-ranking.
Template-C (`type: reranker`) exemplar — the rerank test-harness reference.

## Runtime
- Image: `ghcr.io/huggingface/text-embeddings-inference:89-1.9` (CUDA build for Ada / SM 8.9 / L40S)
- Entry args: `--model-id=/data --port=8080 --dtype=float16 --max-client-batch-size=128`
- API path(s): `POST /v1/rerank` (Cohere-style; gateway → TEI native `/rerank`), `GET /health`

## Resources
- CPU request/limit: init 2/4, server 2/4
- Memory request/limit: init 4Gi/8Gi, server 4Gi/8Gi
- GPU request: **HAMi vGPU slice** — `nvidia.com/gpu: "1"` + `nvidia.com/gpumem: "8192"`; `nodeSelector gpu=on`. Uses ~1.6 GB VRAM (fp16).

## Storage
- PVC name: `bge-reranker-v2-m3-data` (ReadWriteMany, nfs-models, 5Gi)
- Mount path: `/data` (init writes HF weights, server reads readOnly)
- Warm-cache condition: `if [ -f /data/config.json ]` → skip download

## Known quirks
- **No ONNX export (GPU):** TEI's CUDA backend serves the HF safetensors weights directly, so the
  init only downloads weights (the old CPU path exported to ONNX/ORT — removed in the GPU migration).
- **Gateway type-mismatch codes differ by endpoint:** chat-on-rerank → **404**; embed-on-rerank →
  **424** (Failed Dependency). Both are valid rejections — the test accepts any 4xx.
- **Always-on by design:** `minReplicas: 1`. Leave running; do not add `stop=true`.
- Scores are sigmoid-normalized to [0,1].
- **Migrated CPU→GPU (2026-06-28):** was TEI `cpu-1.6` / onnx-fp32 (ORT). Now `89-1.9` (CUDA/Ada) /
  fp16 on a HAMi slice; dropped the ONNX export. Clean delete+redeploy (PVC reused). Gateway 8/3/0;
  rerank-x32 ~86 ms/req.

## Deploy / update steps
1. `kubectl apply -f pvc.yaml` (RWX; caches weights).
2. `kubectl apply -f inferenceservice.yaml` (TEI 89-1.9 CUDA, fp16, HAMi slice, minReplicas 1).
3. `kubectl apply -f details.yaml` (Template-C card; hot-reloads via ConfigMap watch).

## Validation checks
- [x] basic rerank (3 docs → 3 results, sorted)
- [x] top_n respected
- [x] scores descending + in [0,1]
- [x] relevance (semantically matching doc ranks #1)
- [x] model echo + return_documents
- [x] guardrails (chat 404, embed 424, unknown 404)
- [x] catalog entry (type=reranker, ctx 8192)
- [x] no secret values in manifest (HF_TOKEN via hf-token Secret)
