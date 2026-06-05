# climatebert — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: classification (DistilRoBERTa, CPU).
id `climatebert`.

## Scale-up
- Cold start: venv (CPU torch + transformers) + HF snapshot_download of 3 models
  (climatebert/distilroberta-base-climate-f, .../climate-detector, .../netzero-reduction)
  into `HF_HOME=/data/hf-home`; runtime `HF_HUB_OFFLINE=1`. `3/3 Running`.

## Endpoint tests (PASS)

### POST /v1/science/classify (task=netzero)
```bash
curl -s -X POST $GW/v1/science/classify -H 'Content-Type: application/json' \
  -d '{"model":"climatebert","text":"Our company commits to reach net zero emissions by 2050.","task":"netzero"}'
```
→ `prediction=net-zero`, scores {none:0.0005, reduction:0.0007, net-zero:0.9988}. PASS.

### POST /v1/science/classify (task=detect)
```bash
curl -s -X POST $GW/v1/science/classify -H 'Content-Type: application/json' \
  -d '{"model":"climatebert","text":"Rising global temperatures threaten coastal ecosystems.","task":"detect"}'
```
→ `prediction=yes`, scores {no:0.0045, yes:0.9955}. PASS.

### POST /v1/embeddings
```bash
curl -s -X POST $GW/v1/embeddings -H 'Content-Type: application/json' \
  -d '{"model":"climatebert","input":"carbon emissions policy"}'
```
→ 768-dim climate-domain embedding. PASS.

### Catalog
- `GET /v1/models?all=true` → `climatebert` discovered. PASS.

## Not applicable
- OpenAI chat / Anthropic / reasoning: N/A (encoder classifier).

## Card parity
id=climatebert, k8s_name=climatebert, type=classification, dim=768, gpu=false,
endpoints /v1/science/classify (tasks: detect, netzero) + /v1/embeddings.
