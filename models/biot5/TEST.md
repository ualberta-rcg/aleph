# biot5 — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: science-generate (T5, CPU). id `biot5`.

## Scale-up
- Cold start: venv (CPU torch + transformers + sentencepiece) + HF snapshot_download
  (QizhiPei/biot5-base) → `/data/model`, then load. `3/3 Running`. Log: `BioT5 ready.`

## Endpoint tests (PASS)

### POST /v1/science/generate (demo: mol2text)
```bash
curl -s --max-time 200 -X POST $GW/v1/science/generate \
  -H 'Content-Type: application/json' \
  -d '{"model":"biot5","demo":true}'
```
→ HTTP 200, `task=mol2text`, returns SELFIES→text generation. PASS.

### Timing
- Greedy generation on CPU is slow (**~25 s** per request, max_new_tokens=100).
  Not a hang — earlier 30/60 s curl timeouts were cutting off mid-generation.
  Use `--max-time >= 60` when calling.

### Catalog
- `GET /v1/models?all=true` → `biot5` discovered (source QizhiPei/biot5-base). PASS.

## Not applicable
- OpenAI chat / Anthropic / reasoning: N/A (T5 seq2seq science model).

## Card parity
id=biot5, k8s_name=biot5, type=science-generate, gpu=false,
endpoint /v1/science/generate.
