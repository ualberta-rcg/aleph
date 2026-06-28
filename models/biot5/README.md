# biot5 — Cross-modal Chemistry/Biology T5 (BioT5)

`biot5` serves **BioT5** — a cross-modal T5 model bridging molecules (SELFIES/SMILES) and text.
Two task checkpoints: **mol2text** (SMILES → textual description) and **text2mol** (description →
SMILES). CPU-served.

- **Source:** DeepGraphLearning/BioT5 (task-specific checkpoints)
- **Framework:** `transformers` (T5ForConditionalLM) + `selfies` + torch (CPU)

## API

`POST /v1/science/generate`

```json
{ "model": "biot5", "task": "mol2text", "input": "CC(=O)OC1=CC=CC=C1C(=O)O" }
```

`task` is `mol2text` (input = SMILES, → text) or `text2mol` (input = text, → SMILES). The server reads
`task` + `input` (`model` is the gateway routing id).

## Deployment

- Custom FastAPI server (`server.py` embedded in the `biot5-server` ConfigMap, mounted read-only at
  `/app`), run via a persisted venv on the PVC (caduceus pattern). Loads **both** task checkpoints.
- **CPU-only** (no GPU request); runs on workers. Scale-to-zero (`minReplicas: 0`, 15m idle).

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=biot5 \
  python3 models/biot5/test.py
```
Exercises both mol2text (aspirin SMILES) and text2mol directions.
