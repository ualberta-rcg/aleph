# biomedbert — Test Report

Cluster 230, gateway ClusterIP `http://10.43.79.101:80`. Type: embedding (CPU). id `biomedbert-110m`.

## Verified this pass (2026-06-05)

### POST /v1/embeddings — PASS
```bash
curl -s -X POST $GW/v1/embeddings -H 'Content-Type: application/json' \
  -d '{"model":"biomedbert-110m","input":"protein folding and gene expression"}'
```
→ `object=list`, **dim=768**. Input domain: biomedical text (PubMed). PASS.

### Catalog
- `GET /v1/models?all=true` → `biomedbert-110m` present (type=embedding). PASS.

## Not applicable
- OpenAI chat / Anthropic `/v1/messages` / reasoning: N/A (embedding model).

## Card parity
id=biomedbert-110m, type=embedding, dim=768 (verified), gpu=false, scale-to-zero.
