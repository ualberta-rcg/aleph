# bge-reranker-v2-m3 Notes

## Purpose
Always-on multilingual cross-encoder reranker (`/v1/rerank`) for second-stage RAG re-ranking.
Template-C (`type: reranker`) exemplar — the rerank test-harness reference.

## Runtime
- Image: `ghcr.io/huggingface/text-embeddings-inference:cpu-1.6`
- Entry args: `--model-id=/data --port=8080 --dtype=float32 --max-client-batch-size=128`
- API path(s): `POST /v1/rerank` (Cohere-style; gateway → TEI native `/rerank`), `GET /health`

## Resources
- CPU request/limit: init 4/8, server 4/8
- Memory request/limit: init 8Gi/16Gi (ONNX export), server 4Gi/8Gi
- GPU request: **none** (CPU-only; ORT backend)

## Storage
- PVC name: `bge-reranker-v2-m3-data` (ReadWriteMany, nfs-models, 5Gi)
- Mount path: `/data` (init writes HF weights + ONNX export, server reads readOnly)
- Warm-cache condition: sentinel `/data/.onnx-ready` → skip download + ONNX export

## Known quirks
- **ONNX export at deploy:** the init container exports the model to ONNX (ORT backend) the first
  time, gated by `/data/.onnx-ready`. Subsequent cold starts skip it (~10s). A fresh PVC = ~1-2min export.
- **Gateway type-mismatch codes differ by endpoint:** chat-on-rerank → **404**; embed-on-rerank →
  **424** (Failed Dependency). Both are valid rejections — the test accepts any 4xx.
- **Always-on by design:** `minReplicas: 1`. Leave running; do not add `stop=true`.
- Scores are sigmoid-normalized to [0,1].

## Deploy / update steps
1. `kubectl apply -f pvc.yaml` (RWX; caches weights + ONNX).
2. `kubectl apply -f inferenceservice.yaml` (TEI cpu-1.6, minReplicas 1; ONNX export in init).
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
