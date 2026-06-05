# splicebert — Test Report

Cluster 230, gateway ClusterIP `http://10.43.79.101:80`. Type: embedding (CPU). id `splicebert-86m`.

## Verified this pass (2026-06-05)

### POST /v1/embeddings — PASS
```bash
curl -s -X POST $GW/v1/embeddings -H 'Content-Type: application/json' \
  -d '{"model":"splicebert-86m","input":"ACGTACGTACGTACGTTTGGCCAA"}'
```
→ `object=list`, **dim=768**. Input domain: pre-mRNA splice sites. PASS.

### Catalog
- `GET /v1/models?all=true` → `splicebert-86m` present (type=embedding). PASS.

## Not applicable
- OpenAI chat / Anthropic `/v1/messages` / reasoning: N/A (embedding model).

## Card parity
id=splicebert-86m, type=embedding, dim=768 (verified), gpu=false, scale-to-zero.
