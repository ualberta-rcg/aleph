# leandojo — Lean 4 Premise Retriever (LeanDojo)

`leandojo` serves the **LeanDojo** ByT5-small (125M) premise retriever (NeurIPS 2023) — given a Lean
4 proof goal (tactic state), it retrieves relevant premises from Lean's **Mathlib**, ranked by
relevance score. For retrieval-augmented automated theorem proving.

- **Source:** https://huggingface.co/kaiyuy/leandojo-lean4-retriever-byt5-small
- **License:** Apache-2.0
- **Framework:** `transformers` (`AutoModelForSeq2SeqLM`) + torch

## API

`POST /v1/science/retrieve`

```json
{ "model": "leandojo", "goal": "∀ n : ℕ, n + 0 = n", "num_premises": 5 }
```

Returns `premises` (`[{name, score}]`, ranked). The server reads `goal` + `num_premises` (`model` is
the gateway routing id).

## Deployment

- Custom FastAPI server (`server.py` embedded in the `leandojo-server` ConfigMap, mounted read-only at
  `/app`), run via a persisted venv on the PVC (caduceus pattern).
- initContainer builds `/data/venv` (torch + transformers + leandojo) and loads the retriever —
  gated → fast cold starts.
- CPU (no GPU request); runs on workers. Scale-to-zero (`minReplicas: 0`, 15m idle).

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=leandojo \
  python3 models/leandojo/test.py
```
Retrieves premises for `∀ n : ℕ, n + 0 = n`, asserts ranked premise output.
