# CrystaLLM

CrystaLLM-pi_base (~25M, GPT-2 architecture) generates crystal structures in **CIF format** from a chemical formula prompt, using a custom character-level CIF tokenizer (vocab=377). Served by a custom (non-OpenAI) generation server.
[HuggingFace: c-bone/CrystaLLM-pi_base](https://huggingface.co/c-bone/CrystaLLM-pi_base) · MIT

## What it does
- **Crystal generation**: given a formula (`NaCl`, `LiFePO4`, `MgO`, …) it emits CIF-format crystal structures.
- **Custom endpoint** `POST /v1/science/generate` — not chat. No tools / vision / streaming.
- Context window 1024 tokens; ~25M params, GPU float16.

## Call it
```bash
curl $GW/v1/science/generate -H 'Content-Type: application/json' -d '{
  "model": "crysta-llm",
  "formula": "NaCl",
  "max_new_tokens": 400,
  "num_samples": 1,
  "temperature": 1.0
}'
# -> { "model": "crysta-llm", "structures": ["data_NaCl\n...CIF...\n"] }
```

## Resources
- 1× HAMi GPU slice (L40S), custom FastAPI server (`python:3.11-slim` + venv). Weights on PVC `crysta-llm-data`.
- Scale-to-zero: 15-min idle retention, wake-on-demand; cold start ~1-2 min.

## Source
[HuggingFace: c-bone/CrystaLLM-pi_base](https://huggingface.co/c-bone/CrystaLLM-pi_base) (tokenizer: [lantunes/CrystaLLM](https://huggingface.co/lantunes/CrystaLLM)) · MIT
