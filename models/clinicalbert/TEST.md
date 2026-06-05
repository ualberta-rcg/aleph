# clinicalbert — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: embedding (CPU). id `clinicalbert-110m`.

## Scale-up
- Cold start: venv + HF snapshot_download, then load. `3/3 Running`. ~3-4 min.

## Endpoint tests (PASS)
### POST /v1/embeddings (batch)
```bash
curl -s -X POST $GW/v1/embeddings -H "Content-Type: application/json" \
  -d '{"model":"clinicalbert-110m","input":["patient presents with chest pain","aspirin 81mg"]}'
```
→ `count=2, dim=768`. PASS.

### Catalog
- `GET /v1/models?all=true` → `clinicalbert-110m` discovered (embedding). PASS.

## Not applicable
- OpenAI chat / Anthropic / reasoning: N/A (embedding model).

## Card parity
id=clinicalbert-110m, k8s_name=clinicalbert, type=embedding, dim=768 (verified), gpu=false.
