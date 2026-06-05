# specter2 — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: embedding (CPU). id `specter2-110m`.

## Scale-up
- Cold start: venv + HF snapshot_download (allenai/specter2_base) → `/data/model`.
  `3/3 Running`. ~3-4 min cold.

## Endpoint tests (PASS)

### POST /v1/embeddings
```bash
curl -s -X POST $GW/v1/embeddings -H 'Content-Type: application/json' \
  -d '{"model":"specter2-110m","input":"attention is all you need"}'
```
→ 768-dim embedding. PASS.

### Catalog
- `GET /v1/models?all=true` → `specter2-110m` discovered, type=embedding. PASS.

## Not applicable
- OpenAI chat / Anthropic / reasoning: N/A.

## Card parity
id=specter2-110m, k8s_name=specter2, type=embedding, dim=768, gpu=false,
endpoint /v1/embeddings.
