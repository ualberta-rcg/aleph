# chem-t5 — Multitask Chemistry T5

`chem-t5` serves a multitask **Text+Chemistry T5** (GT4SD / MolT5-based) for three chemistry tasks:
**caption** (SMILES → textual description), **forward_synthesis** (reactants → product), and
**retrosynthesis** (product → reactants). CPU-served.

- **Source:** GT4SD task-specific T5 checkpoints
- **Framework:** `transformers` (T5ForConditionalLM) + torch (CPU)

## API

`POST /v1/science/generate`

```json
{ "model": "chem-t5", "task": "caption", "input": "CC(=O)OC1=CC=CC=C1C(=O)O" }
```

`task` ∈ `caption` | `forward_synthesis` | `retrosynthesis`. The server reads `task` + `input` and
returns `output`. (`model` is the gateway routing id.)

## Deployment

- Custom FastAPI server (`server.py` embedded in the `chem-t5-server` ConfigMap, mounted read-only at
  `/app`), run via a persisted venv on the PVC (caduceus pattern).
- **CPU-only** (no GPU request); runs on workers. Scale-to-zero (`minReplicas: 0`, 15m idle).

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=chem-t5 \
  python3 models/chem-t5/test.py
```
Exercises caption (aspirin SMILES) + forward_synthesis.
