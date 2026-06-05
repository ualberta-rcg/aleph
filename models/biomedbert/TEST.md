# biomedbert — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: embedding (CPU). Model id `biomedbert-110m`.

## Scale-up
- Cold start from zero: venv build + HF snapshot_download (~440MB) on first run, then
  server loads. Pod reached `3/3 Running`, `/health` 200. Cold start ~3-4 min.

## Endpoint tests (PASS)

### POST /v1/embeddings (batch)
```bash
curl -s -X POST $GW/v1/embeddings -H "Content-Type: application/json" \
  -d '{"model":"biomedbert-110m","input":["BRCA1 is associated with breast cancer.","aspirin"]}'
```
→ `count=2, dim=768`. PASS.

### Catalog
- `GET /v1/models?all=true` → `biomedbert-110m` discovered (type=embedding, ctx=512). PASS.

## Not applicable
- OpenAI chat / Anthropic / reasoning: N/A (embedding model).

## Card parity
`details.yaml` matches deployed config: id=biomedbert-110m, k8s_name=biomedbert,
type=embedding, context_window=512, embedding_dimensions=768 (verified), gpu=false.
