# BGE-Reranker-v2-M3 (BAAI/bge-reranker-v2-m3)

Multilingual **cross-encoder reranker** for second-stage re-ranking in RAG — scores
(query, document) pairs and sorts by relevance. 100+ languages, up to 8192 tokens. Served
**on GPU via HuggingFace TEI** (Ada/L40S CUDA image, fp16) on a HAMi vGPU slice, always-on.

## Deployment

```bash
kubectl apply -f pvc.yaml             # RWX weights (nfs-models) — downloaded once, reused
kubectl apply -f inferenceservice.yaml # TEI 89-1.9 (CUDA/Ada), fp16, HAMi slice, minReplicas: 1 (always-on)
kubectl apply -f details.yaml          # Template-C card (type: reranker)
```

The init container downloads `BAAI/bge-reranker-v2-m3` to the PVC on first deploy and self-skips
when weights are already present (TEI's CUDA backend serves the safetensors directly — no ONNX).

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
| Framework | HuggingFace TEI `89-1.9` (CUDA/Ada, L40S) |
| Endpoint | `POST /v1/rerank` (Cohere-style → TEI `/rerank`), health `/health` |
| Max input | 8192 tokens (query + document) |
| Scores | sigmoid-normalized to [0,1] |
| Precision | fp16 |
| Parameters | ~568M (XLM-RoBERTa backbone) |
| GPU | HAMi vGPU slice (`nvidia.com/gpu: 1`, `gpumem: 8192`); ~1.6 GB VRAM; `nodeSelector gpu=on` |
| Scale | always-on (`minReplicas: 1`) |
| Weights | PVC `bge-reranker-v2-m3-data` (RWX, nfs-models) |

## Model Highlights

- **Cross-encoder reranker** — more accurate than bi-encoder retrievers; use as the
  second stage after a retriever (e.g. `bge-m3`) in a hybrid RAG pipeline.
- **Multilingual** — 100+ languages.
- **GPU (CUDA) backend** for fast large-batch scoring (fp16 on an L40S HAMi slice).
- Cohere/Jina-compatible `/v1/rerank` (the gateway translates `documents`→`texts`).
