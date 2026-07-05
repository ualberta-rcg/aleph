# Multilingual E5 Small (intfloat/multilingual-e5-small)

~118M-param multilingual embedding model — **384-dim** dense vectors for **100+ languages**.
12-layer MiniLM (Multilingual-MiniLM-L12-H384), mean-pooled + L2-normalized. Custom FastAPI/
transformers server, CPU-only, always-on (minReplicas: 1).

> **Retrieval convention:** prefix queries with `query: ` and passages with `passage: `. For generic
> similarity/clustering, no prefix is needed (the server embeds input as-is).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX weights + venv (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

The init container builds a CPU venv (torch 2.5.1 + transformers 4.44.2 + sentencepiece) and
downloads the model to the PVC on first deploy (idempotent). `server.py` is embedded as the
`multilingual-e5-small-server` ConfigMap.

## Testing

The 11-check multilingual-embedding battery runs inside the gateway pod (first call wakes a
scaled-to-zero model — cold start ~30–60s):

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/multilingual-e5-small/test.py

# Or inside the gateway pod (no auth)
cat models/multilingual-e5-small/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **9 PASS / 2 EXP / 0 FAIL** — dim 384, batch, model-echo, usage,
distinctness (cos 0.86), multilingual (EN/ES/ZH same-sentence cos 0.92), encoding_format,
truncation (>512 tokens), guardrails (chat→embed 404, unknown-model 404), catalog (type=embedding, ctx 512).

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` AutoModel (CPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped), health `/health` |
| Embedding dim | 384 (mean-pooled, L2-normalized) |
| Max input | 512 tokens (tokenizer truncates longer) |
| Languages | 100+ |
| Precision | fp32 |
| Parameters | ~118M (12-layer MiniLM) |
| Scale | always-on (`minReplicas: 1`, max 5, 15m retention) |
| Weights | PVC `multilingual-e5-small` (RWX, nfs-models, 5Gi; bare fleet naming) |

## Model Highlights

- 100+ languages from a compact (~118M) MiniLM backbone — good multilingual retrieval at low cost.
- L2-normalized embeddings; use cosine similarity.
- `query:`/`passage:` asymmetric prefixing for retrieval (not enforced server-side — caller's job).
