# chemberta — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: embedding (CPU). id `chemberta-125m`.

## Scale-up
- Cold start: venv + HF snapshot_download, then load. `3/3 Running`. Cold-start guard
  returns friendly 503 (`model_scaled_to_zero`) until warm. ~3-4 min.

## Endpoint tests (PASS)
### POST /v1/embeddings (batch of 2 SMILES)
```bash
curl -s -X POST $GW/v1/embeddings -H "Content-Type: application/json" \
  -d '{"model":"chemberta-125m","input":["CCO","aspirin"]}'
```
→ `count=2, dim=768`. PASS.

### Catalog
- `GET /v1/models?all=true` → `chemberta-125m` discovered (embedding). PASS.

## Not applicable
- OpenAI chat / Anthropic / reasoning: N/A (embedding model).

## Card parity
id=chemberta-125m, k8s_name=chemberta, type=embedding, dim=768 (verified), gpu=false.
