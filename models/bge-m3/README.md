# BGE-M3 (BAAI/bge-m3)

Multilingual text embedding model — 1024-dim **dense** vectors, plus sparse (lexical) and
multi-vector (ColBERT) retrieval from one model. 100+ languages, up to 8192 tokens. Served
**CPU-only via HuggingFace TEI**, always-on.

## Deployment

```bash
kubectl apply -f pvc.yaml             # RWX weights (nfs-client) — downloaded once, reused
kubectl apply -f inferenceservice.yaml # TEI cpu-1.6, minReplicas: 1 (always-on)
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

The init container downloads `BAAI/bge-m3` to the PVC on first deploy and self-skips when
weights are already present.

## Testing

The 11-check embedding battery runs inside the gateway pod (first call wakes a scaled-down
model through the gateway's 503+ETA; bge-m3 is always-on so it's already warm):

```bash
cat models/bge-m3/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL / 1 SKIP** — dim 1024, batch, model-echo,
usage, encoding_format (float + base64), multilingual, catalog (type=embedding, ctx 8192),
guardrails (chat→embed 404, unknown-model 404). (1 SKIP = truncation — see CLAUDE.md.)

## Key Configuration

| Setting | Value |
|---------|-------|
| Framework | HuggingFace TEI `cpu-1.6` (no GPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped), health `/health` |
| Embedding dim | 1024 (dense; CLS-pooled, L2-normalized) |
| Max input | 8192 tokens |
| Precision | fp32 |
| Parameters | ~568M (XLM-RoBERTa backbone) |
| Scale | always-on (`minReplicas: 1`) |
| Weights | PVC `bge-m3-data` (RWX, nfs-client) |

## Model Highlights

- **Multi-Functionality:** dense + sparse (lexical) + ColBERT (multi-vector) retrieval in one model.
- **Multi-Linguality:** 100+ languages; strong cross-lingual retrieval (MIRACL, MKQA).
- **Multi-Granularity:** short sentences to long documents (up to 8192 tokens).
- **No query instruction prefix** needed (unlike BGE v1.5).
- Only the dense `/v1/embeddings` path is exposed through the gateway; sparse/ColBERT require the
  native TEI `/embed` endpoint or FlagEmbedding directly.
