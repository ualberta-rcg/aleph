# chemberta — Test Report

Cluster 230, gateway ClusterIP `http://10.43.79.101:80`. Type: embedding (CPU). id `chemberta-125m`.

## Verified this pass (2026-06-05)

### POST /v1/embeddings — PASS
```bash
curl -s -X POST $GW/v1/embeddings -H 'Content-Type: application/json' \
  -d '{"model":"chemberta-125m","input":"CCO"}'
```
→ `object=list`, **dim=768**. Input domain: SMILES molecular strings. PASS.

### Catalog
- `GET /v1/models?all=true` → `chemberta-125m` present (type=embedding). PASS.

## Not applicable
- OpenAI chat / Anthropic `/v1/messages` / reasoning: N/A (embedding model).

## Card parity
id=chemberta-125m, type=embedding, dim=768 (verified), gpu=false, scale-to-zero.
