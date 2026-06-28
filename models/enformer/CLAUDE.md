# enformer — Gene-Expression Prediction from DNA (Enformer)

## Source
- HuggingFace: https://huggingface.co/EleutherAI/enformer-official-rough
- License: CC-BY-4.0
- Architecture: Enformer (conv trunk + transformer torso), ~500M params, fp32; 196,608 bp context

## Serving contract (research 2026-06-27)
- **Install:** `transformers<4.52` (compat pin for enformer-pytorch) + `enformer-pytorch` + torch
  (cu126) + `einops` + fastapi/uvicorn/huggingface_hub. Python **3.12** base. Persisted venv on PVC.
- **Weights:** `EleutherAI/enformer-official-rough` via `snapshot_download` → `/data/model` (~500M).
- **API:** `POST /v1/science/predict` {sequence, organism?} → {human_shape, human_mean, human_sample,
  sequence_length}. Server one-hot encodes (ACGTN; pads short seq to 196,608 with N), runs Enformer;
  `out` is a **dict** `{'human','mouse'}` (the deep-fix: `isinstance(out, dict)`). Returns a
  **summary** (the full 896×5313 grid is ~4.7M values — too large for HTTP). `return_tracks:[idx…]`
  selects tracks.
- The `model` field is the gateway routing id (server ignores it) — no collision.

## Deployment (standardized)
- **Pattern:** caduceus — ConfigMap `enformer-server` (server.py embedded) mounted read-only at
  `/app`; initContainer (python:3.12-slim) builds `/data/venv` + downloads weights (gated sentinel);
  main container runs `/data/venv/bin/python /app/server.py`. `/health` startup + readiness probes.
- **PVC:** standalone `pvc.yaml`, name `enformer` (was `enformer-data`, **RWO→RWX**), 10Gi.
- **GPU:** 1× L40S HAMi slice (`gpumem 20480`); fp32; nodeSelector `gpu=on`. Memory 16-32 Gi.
- **Scale-to-zero:** `minReplicas: 0`, 15m idle retention. `progress-deadline: 1800s`, `timeout: 595`.
  Cold start ~4-8 min (venv + ~500M download + Enformer load + first 196kb inference).
- **Card:** v2 Template B (`schema_version: 2`), status `production` (was `broken` — stale).

## Files
- `details.yaml` (v2, `enformer-details`) · `inferenceservice.yaml` (ConfigMap `enformer-server` + ISVC) ·
  `pvc.yaml` (`enformer`) · `test.py` (4kb ACGT → human_shape [896,5313]) · `README.md`.
