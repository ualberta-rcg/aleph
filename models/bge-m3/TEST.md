# bge-m3 — Test Report

Cluster 230, gateway ClusterIP `http://10.43.79.101:80`. Type: embedding (CPU). id `bge-m3`.

## Verified this pass (2026-06-05)

### POST /v1/embeddings (batch, multilingual) — PASS
```bash
curl -s -X POST $GW/v1/embeddings -H 'Content-Type: application/json' \
  -d '{"model":"bge-m3","input":["What is the capital of France?","Comment dire bonjour"]}'
```
→ `object=list`, n=2, **dim=1024**, usage reported. Matches card (`embedding_dimensions: 1024`, ctx 8192). PASS.

### Catalog
- `GET /v1/models?all=true` → `bge-m3` present (type=embedding). PASS.

## Not applicable
- OpenAI chat / Anthropic `/v1/messages` / reasoning: N/A (embedding model).

## Card parity
id=bge-m3, type=embedding, dim=1024 (verified), context_window=8192, gpu=false, scale-to-zero.
