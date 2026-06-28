# ithaca — Ancient Greek Inscription Restoration

`ithaca` serves **Ithaca** (DeepMind × UCL × Venice, *Nature* 2022) — a JAX/Flax transformer that
**restores** damaged ancient Greek inscriptions, **dates** them (BCE), and **geolocates** their
origin. Input is ancient Greek text (50–750 chars, uppercase) with damaged spans marked `[---]`.

- **Source:** https://github.com/google-deepmind/predictingthepast (weights from GCS)
- **License:** Apache-2.0
- **Framework:** `jax[cuda12]` (GPU) + dm-haiku + optax, via the `predictingthepast` library

## API

`POST /v1/science/predict`

```json
{ "model": "ithaca", "text": "ΕΔΟΧΣΕΝ ΤΕΙ ΒΟΥЛЕΕΙ ΚΑΙ ΤΟΙ ΔΕΜΟΙ ... [---] ..." }
```

Returns `restoration` (gap-span predictions) and `attribution` (date BCE + region/subregion). Pass
`"contextualize": true` to add a corpus retrieval search (~2 min, CPU/IO-bound).

## Deployment

- Custom FastAPI server (`server.py` embedded in the `ithaca-server` ConfigMap, mounted read-only at
  `/app`), run via a **persisted venv on the PVC** (caduceus pattern).
- initContainer builds `/data/venv` with **`jax[cuda12]`** (GPU jaxlib — plain `jax` is CPU-only and
  ~3 min/inference) + dm-haiku + optax + fastapi/uvicorn, clones `predictingthepast`, and downloads
  the weights + iphi dataset from GCS — all gated by a sentinel → cold starts skip the install.
- 1× L40S HAMi slice (`gpumem 16384`); fp32; nodeSelector `gpu=on`.
- Scale-to-zero (`minReplicas: 0`, 15m idle retention). Cold start ~3-6 min; first restore/attribute
  JIT-compiles (~90s), then ~8s warm.

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=ithaca \
  python3 models/ithaca/test.py
```
Sends an Attic-decreed fragment, asserts restoration + attribution are returned by **real jax
inference** (not the demo fallback).
