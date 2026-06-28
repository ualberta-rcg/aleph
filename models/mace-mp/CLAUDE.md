# mace-mp — MACE-MP-0 Universal ML Interatomic Potential

## Source
- HuggingFace: https://huggingface.co/ACEsuit/mace-mp-0
- Docs: https://mace-docs.readthedocs.io/en/latest/guide/foundation_models.html
- License: MIT
- Architecture: MACE equivariant MPNN, float64, 89 elements

## Naming note
- Dir / ISVC / card id / k8s_name = **`mace-mp`** (the service). It serves the **MACE-MP-0** model
  weights; `catalog.source` keeps the HF id. This avoids collision with the separate `mace-mp-0` dir
  (which exposes a different `/v1/science/energy` endpoint).

## Serving contract (research 2026-06-27)
- **Install:** `mace-torch>=0.3` (~0.3.16) + `torch` (cu126) + `ase` + `huggingface_hub` +
  `fastapi`/`uvicorn`. Persisted venv on the PVC (gated by sentinel).
- **Weights:** three files from `ACEsuit/mace-mp-0` → `/data/models`: `mace-mp-0b3-medium.model`
  (default), `mace-mp-0b2-small.model`, `mace-mp-0b2-large.model`. Public, no gating.
- **API (MACECalculator):** `MACECalculator(model_paths=<file>, device=, default_dtype="float64")`
  — no `head` arg (single head); variant chosen by file. Stable across mace-torch 0.3.x.
- **Endpoint:** `POST /v1/science/predict` {elements, positions, lattice?, model="medium"} →
  {energy_eV, forces_eV_per_Ang, stress_eV_per_Ang3}.
- **Precision:** float64.

## Deployment (standardized)
- **Pattern:** caduceus — ConfigMap `mace-mp-server` (server.py) mounted read-only at `/app`;
  initContainer builds `/data/venv` + downloads the three weight files; main container runs
  `/data/venv/bin/python /app/server.py` with the data PVC mounted **read-only**. `/health` probes.
- **PVC:** standalone `pvc.yaml`, name `mace-mp`, RWX `nfs-models` 5Gi.
- **GPU:** 1× L40S HAMi slice (`gpumem 10240`); CPU fallback. nodeSelector `gpu=on`.
- **Scale-to-zero:** `minReplicas: 0`, no stop, 15m idle retention.
- **Card:** v2 Template B (`schema_version: 2`), typed input_map/output_map.

## Files
- `details.yaml` (v2, `mace-mp-details`) · `inferenceservice.yaml` (ConfigMap + ISVC) ·
  `pvc.yaml` (`mace-mp`) · `test.py` · `README.md`.

## Notes
- Medium variant loaded at startup; small/large loaded lazily on first request for that size.
- Verify on each deploy: a fresh mace-torch may shift the MACECalculator API.
