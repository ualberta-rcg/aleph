# chemgpt — SMILES Molecule Generation (ChemGPT-1.2B)

`chemgpt` serves **ChemGPT-1.2B** (ncfrey) — a 1.2B-param GPT-Neo model trained on PubChem SMILES.
Autoregressively generates/completes molecules as SMILES strings (de novo drug design). Also exposes
a `/v1/science/embed` endpoint for hidden-state molecular embeddings. **CPU-served.**

- **Source:** https://huggingface.co/ncfrey/ChemGPT-1.2B (gated — needs HF token)
- **License:** MIT
- **Framework:** `transformers` (GPT-Neo) + torch (CPU)

## API

`POST /v1/science/generate`

```json
{ "model": "chemgpt", "smiles": "CCO", "max_new_tokens": 100, "num_return_sequences": 1 }
```

Returns `generated` (a list of SMILES strings). The server reads the `smiles` field (the `model`
field is the gateway routing id). `POST /v1/science/embed` for molecular embeddings.

## Deployment

- Custom FastAPI server (`server.py` embedded in the `chemgpt-server` ConfigMap, mounted read-only at
  `/app`), run via a persisted venv on the PVC (caduceus pattern).
- initContainer builds `/data/venv` (CPU torch + transformers + accelerate) and downloads
  `ncfrey/ChemGPT-1.2B` (gated, HF token) — both gated → fast cold starts.
- **CPU-only** (no GPU request); nodeSelector `gpu=on` keeps it on workers. Knative `timeout: 600`.
- Scale-to-zero (`minReplicas: 0`, 15m idle retention). Cold start ~2-4 min (1.2B on CPU).

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=chemgpt \
  python3 models/chemgpt/test.py
```
Continues a `CCO` SMILES prompt, asserts generated SMILES output.
