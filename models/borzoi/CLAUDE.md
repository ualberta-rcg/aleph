# borzoi — RNA-seq Prediction from Genomic DNA (Borzoi)

## Source
- HuggingFace: https://huggingface.co/johahi/borzoi-replicate-0 (Calico Research, Linder 2023)
- License: CC-BY-4.0
- Architecture: Borzoi (Enformer-variant), ~500M params, fp32; 524,288 bp context

## Serving contract (research 2026-06-27)
- **Install:** `borzoi-pytorch` + torch (cu126) + `transformers<4.51` + `einops` + fastapi/uvicorn.
  Persisted venv on PVC (gated by a `from borzoi_pytorch import Borzoi` import check).
- **Weights:** `johahi/borzoi-replicate-0` via `Borzoi.from_pretrained(...)` → HF cache `/data/hf_cache`
  (`HF_HUB_OFFLINE=1` at runtime).
- **API:** `POST /v1/science/predict` {sequence, n_bins?} → {predictions [n_bins, n_tracks],
  bins_returned, num_tracks, sequence_length}. One-hot encodes (ACGTN; pads short seq to 524,288 with
  N), runs the model, returns the center `n_bins` (default 16). **num_tracks = 6144**.
- The `model` field is the gateway routing id (server ignores it) — no collision.

## Deployment (standardized)
- **Pattern:** caduceus — ConfigMap `borzoi-server` (server.py embedded) mounted read-only at `/app`;
  initContainer builds `/data/venv` + caches weights (gated); main container runs the venv python.
  `/health` startup + readiness probes.
- **PVC:** standalone `pvc.yaml`, name `borzoi` (was `borzoi-data`, **RWO→RWX**), 10Gi.
- **GPU:** 1× L40S HAMi slice (`gpumem 10240`); fp32; nodeSelector `gpu=on`.
- **Scale-to-zero:** `minReplicas: 0`, 15m idle retention. Cold start ~3-6 min.
- **Card:** v2 Template B (`schema_version: 2`).

## Files
- `details.yaml` (v2, `borzoi-details`) · `inferenceservice.yaml` (ConfigMap `borzoi-server` + ISVC) ·
  `pvc.yaml` (`borzoi`) · `test.py` (4kb ACGT, n_bins=4 → [4,6144]) · `README.md`.
