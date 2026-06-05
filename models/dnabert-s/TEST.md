# dnabert-s — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: embedding (CPU). id `dnabert-s`.

## Scale-up
- Cold start: venv (CPU torch + transformers 4.46.3 + sentencepiece + einops) +
  HF snapshot_download (zhihan1996/DNABERT-S) → `/data/model`. `3/3 Running`. ~5 min cold.

## Endpoint tests (PASS)

### POST /v1/embeddings
```bash
curl -s -X POST $GW/v1/embeddings -H 'Content-Type: application/json' \
  -d '{"model":"dnabert-s","input":"ATGCGTACGTTACG"}'
```
→ 768-dim species-aware DNA embedding. PASS.

## Migration fixes
- RawDeployment → Knative; removed GPU nodeSelector (CPU model).
- `endpoints` in card was a JSON list → converted to dict (`primary`, `science`).
- MODEL_ID env var now points to `/data/model` (downloaded in init), not HF hub ID.

### Catalog
- `GET /v1/models?all=true` → `dnabert-s` discovered, type=embedding. PASS.

## Not applicable
- OpenAI chat / Anthropic / reasoning: N/A (DNA encoder).

## Card parity
id=dnabert-s, k8s_name=dnabert-s, type=embedding, dim=768, gpu=false,
endpoints /v1/embeddings + /v1/science/predict.
