# MACE-MH-1 — Multi-Head Foundation Force Field

## Source
- HuggingFace: https://huggingface.co/mace-foundations/mace-mh-1
- Docs: https://mace-docs.readthedocs.io/en/latest/guide/foundation_models.html
- License: ASL (academic/non-commercial)
- Architecture: MACE multi-head equivariant MPNN, float64, 89 elements, 7 heads

## Serving contract (research 2026-06-27)
- **Install:** `mace-torch>=0.3` (resolves to ~0.3.16) + `torch` (cu126) + `ase` + `huggingface_hub`
  + `fastapi`/`uvicorn`. Build a persisted venv on the PVC (gated by sentinel) so cold starts skip it.
- **Weights:** single file `mace-mh-1.model` via `hf_hub_download('mace-foundations/mace-mh-1',
  filename='mace-mh-1.model')` → copied to `/data/models/mace-mh-1.model`. Public repo, no gating.
- **API (MACECalculator):** `MACECalculator(model_paths=..., device='cuda'|'cpu',
  default_dtype='float64', head=head)`. Heads are lazily loaded + cached. `head` API stable across
  mace-torch 0.3.x.
- **Endpoint:** `POST /v1/science/predict` {elements, positions, lattice?, head?} →
  {energy_eV, forces_eV_per_Ang [n][3], stress_eV_per_Ang3 [6] periodic-only}.
- **Precision:** float64 (do NOT half-precision — MACE foundation models require float64 for accuracy).

## Deployment (standardized)
- **Pattern:** caduceus — ConfigMap-embedded `server.py` (`mace-mh-1-server`) mounted at `/app`;
  initContainer builds `/data/venv` + downloads weights; main container runs
  `/data/venv/bin/python3 /app/server.py`. Generous `/health` startup + readiness probes.
- **PVC:** standalone `pvc.yaml`, name `mace-mh-1`, RWX `nfs-models` 5Gi.
- **GPU:** 1× L40S HAMi slice (`gpumem 16384`); CPU fallback. nodeSelector `gpu=on`.
- **Scale-to-zero:** `minReplicas: 0`, no stop, 15m idle retention.
- **Card:** v2 Template B (`schema_version: 2`), typed input_map/output_map.

## Files
- `details.yaml` — v2 card (ConfigMap `mace-mh-1-details`, label `model-details: "true"`)
- `inferenceservice.yaml` — ConfigMap (`mace-mh-1-server`) + ISVC (server.py embedded)
- `pvc.yaml` — standalone RWX PVC (`mace-mh-1`)
- `test.py` — force-field battery (Cu cell → energy/forces/stress shape + sanity)
- `README.md` — overview

## Notes
- Heads are lazily loaded into a `calc_cache` dict; first request after cold-start loads `omat_pbe`.
- Verify on each deploy: a fresh mace-torch may shift the MACECalculator API — check the server logs
  if `head=`/`model_paths=` raise.
