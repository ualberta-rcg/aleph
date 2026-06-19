# prokbert Notes

## Purpose
Prokaryotic (bacterial) DNA embedding service (384-dim mean-pooled) for phage/promoter/genomics tasks.
Template-C (`type: embedding`), no-PVC variant (loads from HF hub).

## Runtime
- Image: `python:3.11-slim`; container installs `torch` (cu121) + `transformers==4.46.3` on start, then runs `/app/server.py`
- server.py: `prokbert-server` ConfigMap (mounted `/app`); AutoTokenizer/AutoModel, trust_remote_code
- API: `POST /v1/embeddings` (OpenAI; + `/v1/science/predict`), `GET /health`
- No PVC — `HF_HOME=/tmp/hf_cache` (ephemeral); re-downloads + pip-installs every cold start (small model).

## Resources
- CPU/Mem: 1/2Gi req, 2/4Gi limit
- GPU: HAMi `nvidia.com/gpumem: 3072`

## Known quirks
- **384-dim** (not 768 — the ISVC header comment was wrong; card is correct).
- **`usage` added 2026-06-19** — the handler previously omitted it (OpenAI-compliance fix).
- model echo is `prokbert-mini` (card id `prokbert`, ISVC `prokbert`).
- 6-mer LCA tokenizer; truncates to 1024 tokens.
- Scale-to-zero (`minReplicas: 0`); slowish cold start (pip install + download each time).

## Deploy / update steps
1. `kubectl apply -f inferenceservice.yaml` (ConfigMap server.py + ISVC).
2. `kubectl apply -f details.yaml` (Template-C card).
> After changing server.py: restart the pod (stop toggle / delete pod) so it reloads the ConfigMap.

## Validation checks
- [x] dim == 384, batch, model-echo, usage, distinctness, encoding_format, truncation, guardrails, catalog
- [x] no secret values (public model; HF_TOKEN not required)
