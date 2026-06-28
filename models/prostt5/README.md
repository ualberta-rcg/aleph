# prostt5 — Protein AA ↔ 3Di Structure Translation (ProstT5)

`prostt5` serves **ProstT5** (Rostlab, ~800M) — a T5 seq2seq model that translates between protein
amino-acid sequences and **3Di** (3-state discrete) structure tokens. Fast structure prediction
without MSA. Supports `seq2struct` (AA→3Di) and `struct2seq` (3Di→AA).

- **Source:** https://huggingface.co/Rostlab/ProstT5
- **License:** MIT
- **Framework:** `transformers==4.40.2` (`T5ForConditionalGeneration`) + sentencepiece + torch (CUDA)

## API

`POST /v1/translate`

```json
{ "model": "prostt5", "input": "MKTVVRQEL", "direction": "seq2struct" }
```

`input` is the AA sequence (seq2struct) or 3Di tokens (struct2seq). Returns `results` (translated
sequences). The server reads `input` + `direction` (`model` is the gateway routing id).

## Deployment

- Custom FastAPI server (`server.py` embedded in the `prostt5-server` ConfigMap, mounted read-only at
  `/app`), run via a persisted venv on the PVC (caduceus pattern).
- initContainer builds `/data/venv` (torch cu126 + **`transformers==4.40.2`** + sentencepiece) and
  downloads `Rostlab/ProstT5` — gated → fast cold starts.
- 1× L40S HAMi slice (`gpumem` per ISVC); fp16 on GPU. nodeSelector `gpu=on`.
- Scale-to-zero (`minReplicas: 0`, 15m idle retention). Cold start ~3-6 min.

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=prostt5 \
  python3 models/prostt5/test.py
```
Translates an AA sequence to 3Di tokens (asserts lowercase 3Di output).
