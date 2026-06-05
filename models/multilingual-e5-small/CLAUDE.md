# Multilingual E5 Small -- Model Context

## What This Model Does

Multilingual E5 Small (intfloat/multilingual-e5-small) is a 12-layer, 384-dimensional embedding model supporting 100 languages. Initialized from microsoft/Multilingual-MiniLM-L12-H384 and trained with contrastive learning on billions of text pairs across multiple stages (weak supervision pretraining + supervised fine-tuning). Requires "query: " or "passage: " prefix for best retrieval results. Max 512 tokens. Deployed via HuggingFace Text Embeddings Inference (TEI) for maximum throughput.

## Source Repo

**HuggingFace**: [intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small)

- **License**: Apache-2.0
- **Architecture**: 12-layer transformer (MiniLM, 384 hidden dim)
- **Paper**: "Multilingual E5 Text Embeddings: A Technical Report" (Wang et al., arXiv 2024)
- **Prefix requirement**: Use "query: " for queries and "passage: " for passages in retrieval tasks. Use "query: " for symmetric tasks (similarity, clustering).

## How The Server Works

- **Pattern**: HuggingFace Text Embeddings Inference (TEI) + init container download
- **Container**: `ghcr.io/huggingface/text-embeddings-inference:cpu-1.6` running with `--model-id=/data --port=8080 --dtype=float32`
- **Init container**: `python:3.11-slim` downloads model from HF to PVC (idempotent via config.json check)
- **PVC**: `multilingual-e5-small-data` (5Gi, NFS) -- stores model weights only
- **Health**: TEI's built-in `/health` endpoint
- **GPU**: None (CPU-only)
- **Startup**: ~30 seconds
- **API**: TEI native `/embed` endpoint (not OpenAI-style). Gateway translates requests.
- **Probes**: K8s readiness probe on `/health`

## Our Config vs Source Recommendations

| Aspect | Source | Our Config | Notes |
|--------|--------|-----------|-------|
| Pooling | average_pool with attention mask | TEI handles pooling internally | Correct |
| Prefix | "query: " / "passage: " | User responsibility | Cannot enforce at server level |
| Max tokens | 512 | 512 (--max_batch_requests handled by TEI) | Correct |
| Normalization | L2 normalize recommended | TEI handles this | Correct |
| Precision | float32 | float32 | Correct for CPU |

## Gateway Integration

- **ISVC name**: `multilingual-e5-small` (matches API id)
- **MODEL_TYPE**: embedding
- **KSERVE_CUSTOM_MODELS**: yes -- uses `/v1/` prefix
- **NOT in GPU_MODELS**: CPU-only
- **CONTEXT_WINDOWS**: 512
- **minReplicas**: 1 (always-on)
- **NOT in _CUSTOM_HEALTH_MODELS**: Uses standard K8s readiness probe

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/multilingual-e5-small/

# Force update
kubectl apply --server-side --force-conflicts -k models/multilingual-e5-small/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=multilingual-e5-small

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=multilingual-e5-small -c kserve-container -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"multilingual-e5-small","input":"query: What is machine learning?"}'
```

## Known Issues / Optimization Opportunities

1. **No configMapGenerator**: Unlike other models, there is no server.py or configMapGenerator since TEI is the server. This is correct.

2. **Always-on**: minReplicas=1 means it always consumes CPU resources. Could be set to 0 for scale-to-zero.

3. **TEI version pinned to cpu-1.6**: Specific version is good for reproducibility but may miss performance improvements in newer versions.

4. **No max_batch_requests/limit**: TEI has configurable concurrency limits that are not explicitly set. Uses TEI defaults.

5. **Prefix awareness**: The server does not enforce or validate the "query: "/"passage: " prefix convention. Users must remember to add it.

6. **Init container idempotent**: Yes -- checks for /data/config.json before downloading.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ISVC spec (TEI container + init download) |
| `kustomization.yaml` | Kustomize resources |
| `pvc.yaml` | Dedicated PVC (multilingual-e5-small-data, 5Gi NFS) |
| `README.md` | Original documentation |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
