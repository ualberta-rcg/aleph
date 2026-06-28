# chgnet — CHGNet Universal NN Potential (magnetic moments + charge)

## Source
- GitHub: https://github.com/CederGroupHub/chgnet
- License: MIT
- Architecture: CHGNet (Charge-Enhanced Graph Neural Network), float32, ~2M params

## Serving contract (research 2026-06-27)
- **Install:** `chgnet==0.3.8` (pinned — 0.4.x removes the `atom_features_type` kwarg from
  `CrystalGraph` but the bundled model's graph converter still passes it → `unexpected keyword
  argument`). Pulls torch + pymatgen + ase. Persisted venv on the PVC (gated by `/data/venv/bin`).
- **Weights:** the HF repo `CederGroupHub/chgnet` was **removed (404)** — the init's `hf_hub_download`
  is best-effort and **non-fatal**; the server falls back to `CHGNet.load()` (the **bundled**
  pretrained weights shipped in the pip package). So no gating, no external weights needed.
- **API:** `POST /v1/science/energy` {structure:{elements, positions, cell?, pbc?}} →
  {energy_eV, energy_eV_per_atom, forces_eV_per_A, stress_GPa, magmom_muB, n_atoms}. Body uses a
  **nested `structure`** (pymatgen `Structure`). A large cubic box is synthesized for molecules.
  Inference via `model.predict_structure()`.
- **CHGNet-unique:** also returns **per-atom magnetic moments** (`magmom_muB`) — its differentiator.
- Works on torch 2.12 + numpy 2.4 (no pin needed at 0.3.8).

## Deployment (standardized)
- **Pattern:** caduceus — ConfigMap `chgnet-server` with **`server.py` embedded** (was previously a
  standalone file built into the ConfigMap via `kustomization.yaml`; now embedded for the flat-`apply`
  standard — standalone `server.py` + `kustomization.yaml` dropped). Mounted at `/app`; initContainer
  builds `/data/venv` + best-effort caches checkpoint; main container runs
  `/data/venv/bin/python /app/server.py`. `/health` startup + readiness probes.
- **PVC:** standalone `pvc.yaml`, name `chgnet` (was `chgnet-data`), RWX `nfs-models`.
- **GPU:** 1× L40S HAMi slice (`gpumem 8192`); CPU fallback. nodeSelector `gpu=on`.
- **Scale-to-zero:** `minReplicas: 0`, no stop, 15m idle retention. Cold start ~1-2 min (first
  inference compiles torch ops — slow).
- **Card:** v2 Template B (`schema_version: 2`), id `chgnet` (was `chgnet-v0.3` + an `isvc_name_map`
  hack — now id = ISVC name, no remap).

## Files
- `details.yaml` (v2, `chgnet-details`) · `inferenceservice.yaml` (ConfigMap `chgnet-server` + ISVC) ·
  `pvc.yaml` (`chgnet`) · `test.py` · `README.md`.

## Notes
- The deep-fix history: an earlier ported `server.py` built `CrystalGraph` with a bad kwarg; this one
  uses `model.predict_structure()` directly (the canonical CHGNet API). Verified on 43.
