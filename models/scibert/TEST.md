# scibert — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: embedding (CPU). id `scibert-110m`.

## Scale-up
- Cold start: venv (CPU torch + transformers) + HF snapshot_download
  (allenai/scibert_scivocab_uncased) → `/data/model`. `3/3 Running`. ~3-4 min cold.

## Endpoint tests (PASS)

### POST /v1/embeddings (batch)
```bash
curl -s -X POST $GW/v1/embeddings -H 'Content-Type: application/json' \
  -d '{"model":"scibert-110m","input":["protein folding mechanisms","deep learning"]}'
```
→ 768-dim embeddings for 2 inputs. PASS.

### Catalog
- `GET /v1/models?all=true` → `scibert-110m` discovered, type=embedding. PASS.

## Not applicable
- OpenAI chat / Anthropic / reasoning: N/A.

## Card parity
id=scibert-110m, k8s_name=scibert, type=embedding, dim=768, gpu=false,
endpoint /v1/embeddings.
