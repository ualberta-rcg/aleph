# mace-mp-0 — MACE-MP-0 Force Field (CPU, /v1/science/energy)

## Source
- GitHub: https://github.com/ACEsuit/mace · model: https://github.com/ACEsuit/mace-mp/releases
- License: MIT
- Architecture: MACE equivariant MPNN, float32, 89 elements

## Serving contract (research 2026-06-27)
- **Install:** `mace-torch` (~0.3.16, pulls `mace_mp()` helper) + **CPU** `torch`
  (`--extra-index-url https://download.pytorch.org/whl/cpu`) + `ase` + `fastapi`/`uvicorn`.
  Persisted venv on the PVC (gated by `/data/venv/bin`).
- **Weights:** the medium checkpoint `2023-12-03-mace-128-L1_epoch-199.model` downloaded via
  `urllib` from the ACEsuit/mace-mp GitHub releases → cached at `/data/mace-models/medium.model`
  (so cold starts skip the 42 MB re-download). `mace_mp(model=<local>, device="cpu",
  default_dtype="float32")`.
- **Endpoint:** `POST /v1/science/energy` {structure:{elements, positions, cell?, pbc?}} →
  {energy_eV, forces_eV_A, stress_eV_A3}. Body takes a **nested `structure`** object.
- **Precision:** float32 (CPU). Note: a zero/None cell with PBC gives garbage energies — the server
  defaults to non-periodic when no cell is supplied.
- Distinct from `mace-mp` (GPU /v1/science/predict, small/medium/large + float64).

## Deployment (standardized)
- **Pattern:** caduceus — ConfigMap `mace-mp-0-server` (server.py) mounted read-only at `/app`;
  initContainer builds `/data/venv` + caches the model; main container runs
  `/data/venv/bin/python /app/server.py` with the data PVC read-only. `/health` startup + readiness probes.
- **PVC:** standalone `pvc.yaml`, name `mace-mp-0`, RWX `nfs-models` 5Gi.
- **Compute:** **CPU-only** (no GPU request; no `gpu=on` nodeSelector) — runs on any worker. 8–16 CPU.
- **Scale-to-zero:** `minReplicas: 0`, no stop, 15m idle retention. Cold start ~2-4 min on CPU.
- **Card:** v2 Template B (`schema_version: 2`), typed input_map (nested structure)/output_map.
- Dropped `kustomization.yaml` (flat-dir standard).

## Files
- `details.yaml` (v2, `mace-mp-0-details`) · `inferenceservice.yaml` (ConfigMap + ISVC) ·
  `pvc.yaml` (`mace-mp-0`) · `test.py` · `README.md`.

## Notes
- The `model` field is the gateway routing id (`mace-mp-0`); this server has no variant selector, so
  no routing collision (unlike `mace-mp`).
- Verify on each deploy: a fresh mace-torch may shift the `mace_mp()` API or numpy pin.
