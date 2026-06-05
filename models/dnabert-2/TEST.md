# dnabert-2 — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: embedding (CPU). id `dnabert-2-117m`.

## Scale-up
- Cold start: venv (CPU torch + transformers) + HF snapshot_download
  (zhihan1996/DNABERT-2-117M) → `/data/model`. `3/3 Running`. ~4-5 min cold.

## Endpoint tests (PASS)

### POST /v1/embeddings
```bash
curl -s -X POST $GW/v1/embeddings -H 'Content-Type: application/json' \
  -d '{"model":"dnabert-2-117m","input":"ATGCGTACGTTACG"}'
```
→ 768-dim DNA embedding. PASS.

## Migration fix
- `pt_model(**enc)` returned a tuple, not a `ModelOutput`. Fixed to use
  `raw[0]` as the hidden states when `.last_hidden_state` is not available.

### Catalog
- `GET /v1/models?all=true` → `dnabert-2-117m` discovered, type=embedding. PASS.

## Not applicable
- OpenAI chat / Anthropic / reasoning: N/A (DNA encoder).

## Card parity
id=dnabert-2-117m, k8s_name=dnabert-2, type=embedding, dim=768, gpu=false,
endpoint /v1/embeddings.
