# pubmedbert — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: embedding (CPU). id `pubmedbert`.

## Scale-up
- Cold start: venv (CPU torch + transformers) + HF snapshot_download
  (microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract) → `/data/model`. `3/3 Running`.

## Endpoint tests (PASS)

### POST /v1/embeddings
```bash
curl -s -X POST $GW/v1/embeddings -H 'Content-Type: application/json' \
  -d '{"model":"pubmedbert","input":"BRCA1 mutation increases cancer risk"}'
```
→ 768-dim embedding. Model reports as `pubmedbert-110m`. PASS.

### Catalog
- `GET /v1/models?all=true` → `pubmedbert` discovered, type=embedding. PASS.
- Note: use model id `pubmedbert` in requests (not `pubmedbert-110m`).

## Not applicable
- OpenAI chat / Anthropic / reasoning: N/A.

## Card parity
id=pubmedbert, k8s_name=pubmedbert, type=embedding, dim=768, gpu=false,
endpoint /v1/embeddings.

## Built from scratch
Source was a stub-only directory on 232. Server built using biomedbert pattern.
