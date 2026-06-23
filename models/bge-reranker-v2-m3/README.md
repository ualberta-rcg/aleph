# BGE-Reranker-v2-M3 (BAAI/bge-reranker-v2-m3)

Multilingual **cross-encoder reranker** for second-stage re-ranking in RAG — scores
(query, document) pairs and sorts by relevance. 100+ languages, up to 8192 tokens. Served
**CPU-only via HuggingFace TEI on the ONNX/ORT backend**, always-on.

## Deployment

```bash
kubectl apply -f pvc.yaml             # RWX weights (nfs-models); ONNX export cached here too
kubectl apply -f inferenceservice.yaml # TEI cpu-1.6, minReplicas: 1 (always-on)
kubectl apply -f details.yaml          # Template-C card (type: reranker)
```

The init container downloads `BAAI/bge-reranker-v2-m3` and exports it to ONNX once
(gated by a `/data/.onnx-ready` sentinel), so subsequent cold starts skip the export.

## Testing

The 11-check rerank battery runs inside the gateway pod:

```bash
cat models/bge-reranker-v2-m3/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 3 EXP / 0 FAIL** — basic rerank, top_n, descending
scores in [0,1], correct-doc-ranked-#1 (relevance), model-echo, return_documents,
guardrails (chat→404, embed→424, unknown-model 404), catalog (type=reranker).

## Key Configuration

| Setting | Value |
|---------|-------|
| Framework | HuggingFace TEI `cpu-1.6` (ORT/ONNX backend, no GPU) |
| Endpoint | `POST /v1/rerank` (Cohere-style → TEI `/rerank`), health `/health` |
| Max input | 8192 tokens (query + document) |
| Scores | sigmoid-normalized to [0,1] |
| Precision | onnx-fp32 |
| Parameters | ~568M (XLM-RoBERTa backbone) |
| Scale | always-on (`minReplicas: 1`) |
| Weights | PVC `bge-reranker-v2-m3-data` (RWX, nfs-models; ONNX cached) |

## Model Highlights

- **Cross-encoder reranker** — more accurate than bi-encoder retrievers; use as the
  second stage after a retriever (e.g. `bge-m3`) in a hybrid RAG pipeline.
- **Multilingual** — 100+ languages.
- **ONNX/ORT** export for fast large-batch scoring (exported once at deploy via sentinel).
- Cohere/Jina-compatible `/v1/rerank` (the gateway translates `documents`→`texts`).
