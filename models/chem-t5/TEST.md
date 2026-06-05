# chem-t5 — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: science-generate (T5, CPU). id `chem-t5`.

## Scale-up
- Cold start: venv (CPU torch + transformers + sentencepiece) + HF snapshot_download
  (GT4SD/multitask-text-and-chemistry-t5-base-standard) → `/data/model`, then load.
  `3/3 Running`.

## Endpoint tests (PASS)

### POST /v1/science/generate (demo: forward_synthesis)
```bash
curl -s --max-time 60 -X POST $GW/v1/science/generate \
  -H 'Content-Type: application/json' \
  -d '{"model":"chem-t5","demo":true}'
```
→ HTTP 200:
```json
{"task":"forward_synthesis",
 "input":"CC(=O)Oc1ccccc1C(=O)O.CCO",
 "output":"CCOC(=O)c1ccccc1OC(C)=O","model":"chem-t5"}
```
PASS — valid aspirin esterification product. Beam search (num_beams=4),
completes in ~10 s on CPU.

### Catalog
- `GET /v1/models?all=true` → `chem-t5` discovered. PASS. Supports tasks:
  forward_synthesis, retrosynthesis, paragraph_to_actions, mol2text, text2mol, etc.

## Not applicable
- OpenAI chat / Anthropic / reasoning: N/A (T5 seq2seq chemistry model).

## Card parity
id=chem-t5, k8s_name=chem-t5, type=science-generate, gpu=false,
endpoint /v1/science/generate.
