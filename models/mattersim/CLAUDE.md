# mattersim — Microsoft MatterSim Universal Atomistic Force Field

## Source
- HuggingFace: https://huggingface.co/microsoft/mattersim · arXiv: 2405.04967
- License: MIT
- Architecture: MatterSim deep-learning atomistic model, float32, ~1M params

## Serving contract (research 2026-06-27)
- **Install:** `mattersim` + `torch`/`torchaudio`/`torchvision` (cu126) + `torch_geometric`
  (PyG wheel for the torch build) + `ase`. Needs `git` + `build-essential` in the init for compiles.
  Persisted venv on the PVC (gated by a `from mattersim.forcefield import MatterSimCalculator`
  import check).
- **Weights:** the MatterSim checkpoint auto-downloads (from microsoft/mattersim GitHub raw) on first
  `MatterSimCalculator()` load. Cached to `/root/.local/mattersim/...` (ephemeral) — the init's gate
  checks a different PVC path, so cold starts re-download the small 1M checkpoint (~1s, non-fatal).
- **API:** `POST /v1/science/predict` {elements, positions, lattice?} →
  {energy_ev, energy_per_atom_ev, forces_ev_per_angstrom, stress_ev_per_angstrom3 (voigt 6),
  stress_gpa (periodic)}. `POST /v1/science/relax` {…, fmax?, steps?} → BFGS-relaxed structure
  ({converged, steps, energy_ev, relaxed_positions, relaxed_cell}).
- The `model` field is the gateway routing id (server ignores it) — no collision.
- **Cold start is slow** (~3-4 min: mattersim + torch_geometric import + load) — may exceed a 6-min
  wake window on the very first deploy; re-run the test warm.

## Deployment (standardized)
- **Pattern:** caduceus — ConfigMap `mattersim-server` (server.py embedded) mounted read-only at
  `/app`; initContainer builds `/data/venv` + pre-caches the checkpoint; main container runs
  `/data/venv/bin/python /app/server.py`. `/health` startup + readiness probes.
- **PVC:** standalone `pvc.yaml`, name `mattersim` (was `mattersim-data`, **RWO→RWX**), 10Gi.
- **GPU:** 1× L40S HAMi slice (`gpumem 10240`); CPU fallback. nodeSelector `gpu=on`.
- **Scale-to-zero:** `minReplicas: 0`, no stop, 15m idle retention.
- **Card:** v2 Template B (`schema_version: 2`), nested predict/relax input_map/output_map.

## Server fixes applied (2026-06-27)
- `predict` stress → `voigt=True` (flat 6, fleet-consistent; was `voigt=False` 3×3).
- `relax` → `bool(opt.converged())` + `int(opt.get_number_of_steps())` (numpy types that FastAPI
  couldn't JSON-serialize → 500).

## Files
- `details.yaml` (v2, `mattersim-details`) · `inferenceservice.yaml` (ConfigMap `mattersim-server` + ISVC) ·
  `pvc.yaml` (`mattersim`) · `test.py` (predict + relax) · `README.md`.
