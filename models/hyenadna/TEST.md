# hyenadna — Test Report

Cluster 230, gateway ClusterIP `http://10.43.79.101:80`. Type: embedding (CPU). id `hyenadna-6.5m`.

## Verified this pass (2026-06-05)

### POST /v1/embeddings — PASS
```bash
curl -s -X POST $GW/v1/embeddings -H 'Content-Type: application/json' \
  -d '{"model":"hyenadna-6.5m","input":"ACGTACGTACGTACGTTTGGCCAA"}'
```
→ `object=list`, **dim=256**. Input domain: long-range DNA sequences. PASS.

### Catalog
- `GET /v1/models?all=true` → `hyenadna-6.5m` present (type=embedding). PASS.

## Not applicable
- OpenAI chat / Anthropic `/v1/messages` / reasoning: N/A (embedding model).

## Card parity
id=hyenadna-6.5m, type=embedding, dim=256 (verified), gpu=false, scale-to-zero.
