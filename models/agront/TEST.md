# agront — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: embedding (DNA LM, GPU). id `agront`.

## Scale-up
- Cold start from zero: venv build (cu121 torch) + HF snapshot_download of the 1B model
  (~4GB) to PVC, then GPU load. Pod `3/3 Running`, `/health` 200. Cold start ~4-5 min.
- HAMi placement: 1 vGPU slice, `nvidia.com/gpumem: 8192`.

## Endpoint tests (PASS)

### POST /v1/embeddings
```bash
curl -s -X POST $GW/v1/embeddings -H "Content-Type: application/json" \
  -d '{"model":"agront","input":"ATGGCGCCTGACTCGAGTAAGCTTAGCTAGCTAGCATCGATCG..."}'
```
→ `dim=1500`, first3=`[0.2171, 0.1101, 0.058]`. PASS.

### POST /v1/science/predict
```bash
curl -s -X POST $GW/v1/science/predict -H "Content-Type: application/json" \
  -d '{"model":"agront","sequence":"ATGGCGCCTGACTCGAGTAAG"}'
```
→ `dims=1500, sequence_length=21`. PASS.

### Catalog
- `GET /v1/models?all=true` → `agront` discovered (type=embedding, gpu=true). PASS.

## Card correction
- Old 232 card/header claimed 1280-dim; **actual output is 1500-dim** (verified).
  Card updated to `embedding_dimensions: 1500`.

## Not applicable
- OpenAI chat / Anthropic / reasoning: N/A (DNA embedding model).
