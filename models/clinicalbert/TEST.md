# clinicalbert — Test Report

Cluster 230, gateway ClusterIP `http://10.43.79.101:80`. Type: embedding (CPU). id `clinicalbert-110m`.

## Verified this pass (2026-06-05)

### POST /v1/embeddings — PASS
```bash
curl -s -X POST $GW/v1/embeddings -H 'Content-Type: application/json' \
  -d '{"model":"clinicalbert-110m","input":"patient presents with acute chest pain"}'
```
→ `object=list`, **dim=768**. Input domain: clinical notes. PASS.

### Catalog
- `GET /v1/models?all=true` → `clinicalbert-110m` present (type=embedding). PASS.

## Not applicable
- OpenAI chat / Anthropic `/v1/messages` / reasoning: N/A (embedding model).

## Card parity
id=clinicalbert-110m, type=embedding, dim=768 (verified), gpu=false, scale-to-zero.
