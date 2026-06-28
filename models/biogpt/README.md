# biogpt — Biomedical Text Generation (BioGPT)

`biogpt` serves **BioGPT** (Microsoft, 347M) — a GPT-2-style autoregressive LM pre-trained on 15M
PubMed abstracts. Generates biomedical text from a prompt (drug/protein/disease descriptions,
relation extraction).

- **Source:** https://huggingface.co/microsoft/biogpt
- **License:** MIT
- **Framework:** `transformers` (`BioGptForCausalLM`) + torch (CUDA 12.6); fp16 on GPU

## API

`POST /v1/completions`

```json
{ "model": "biogpt", "prompt": "The treatment of diabetes includes", "max_tokens": 100 }
```

Returns `choices` (`[{text, index, finish_reason}]`).

## Deployment

- Custom FastAPI server (`server.py` embedded in the `biogpt-server` ConfigMap, mounted read-only at
  `/app`), run via a persisted venv on the PVC (caduceus pattern).
- initContainer builds `/data/venv` (torch cu126 + transformers + sacremosomes) and caches
  `microsoft/biogpt` — both gated → fast cold starts.
- 1× L40S HAMi slice (`gpumem 8192`); fp16 on GPU. nodeSelector `gpu=on`.
- Scale-to-zero (`minReplicas: 0`, 15m idle retention).

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=biogpt \
  python3 models/biogpt/test.py
```
Continues a biomedical prompt, asserts non-trivial text output.
