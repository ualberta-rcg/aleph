# aurora — Microsoft Aurora Atmospheric Foundation Model

`aurora` serves **Microsoft Aurora** (microsoft/aurora, ~1.3B, Nature 2025) — a foundation model for
the Earth system. Predicts global weather (wind, temperature, humidity, pressure) at 0.25° in 6-hour
steps. Surface + atmospheric variables at 13 pressure levels. Transformer with spherical harmonics.

- **Source:** https://huggingface.co/microsoft/aurora · **License:** MIT
- **Framework:** `microsoft-aurora` (`AuroraSmallPretrained`) + torch

## API
`POST /v1/science/forecast` — `{ surf_vars: {2t, 10u, 10v, msl}, atmos_vars: {t, u, v, q, z}, lat, lon, time, atmos_levels }`
→ `{ surf_vars, atmos_vars, step: "6h" }` (6-hour forecast ahead).

## Deployment
Custom FastAPI server (ConfigMap-embedded `aurora-server`), persisted venv on PVC (caduceus pattern).
initContainer builds `/data/venv` (torch cu126 + microsoft-aurora) + downloads the checkpoint, gated.
`progress-deadline: 1800s`. 1× L40S HAMi slice (`gpumem 16384`); nodeSelector `gpu=on`. Scale-to-zero.

## Test
```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=aurora \
  python3 models/aurora/test.py
```
