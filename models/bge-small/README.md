# BGE-small-en-v1.5 (BAAI/bge-small-en-v1.5)

The smallest BGE v1.5 **English** embedding model — 384-dim dense vectors for fast retrieval
over short text. ~33M params. Served **CPU-only via HuggingFace TEI**, always-on. TEI fetches
the ~130 MB public model itself on start, so there is **no PVC**.

## Deployment

```bash
kubectl apply -f inferenceservice.yaml # TEI cpu-latest, minReplicas: 1 (fetches the model on start)
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

No PVC — the model is small and public, fetched directly by TEI into its container cache.

## Testing

The 11-check embedding battery runs inside the gateway pod (first call wakes the model —
TEI downloads the ~130 MB weights on first start):

```bash
cat models/bge-small/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **9 PASS / 2 EXP / 0 FAIL** — dim 384, batch, model-echo, usage,
distinctness (cos 0.53), encoding_format float+base64, truncation (>512 tokens), guardrails
(chat→embed 404, unknown-model 404), catalog (type=embedding, ctx 512).

## Key Configuration

| Setting | Value |
|---------|-------|
| Framework | HuggingFace TEI `cpu-latest` (no GPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped), health `/health` |
| Embedding dim | 384 (CLS-pooled, L2-normalized) |
| Max input | 512 tokens |
| Precision | fp32 |
| Parameters | ~33M (6 layers) |
| Scale | always-on (`minReplicas: 1`) |
| Weights | none (TEI fetches the public model on start) |

## Model Highlights

- Smallest BGE v1.5 model — fastest, lowest footprint; good for high-volume short-text retrieval.
- English; **no query instruction prefix** needed (BGE v1.5 convention).
- 384-dim CLS-pooled, L2-normalized embeddings.
