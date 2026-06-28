# diffdock — DiffDock-L Protein-Ligand Docking

## Source
- GitHub: https://github.com/gcorso/DiffDock (image `rbgcsail/diffdock:v1.1.3`)
- License: MIT
- Architecture: diffusion score model + confidence model; ESM-2 protein embeddings; ~20M params; fp32

## Serving contract (research 2026-06-27)
- **Runtime:** the **`rbgcsail/diffdock:v1.1.3`** image (conda env `diffdock` with rdkit + ESM-2 +
  torch-geometric pre-built). The FastAPI server runs on that image's Python; **server deps**
  (fastapi/uvicorn, pinned for Python 3.9: `fastapi==0.103.2`, `uvicorn==0.23.2`, `starlette==0.27`,
  `pydantic<2`, `click<8.2` — 8.2+ uses 3.10 match-syntax; the conda env is 3.9) are installed to
  `/data/pylibs39` by the init and injected via `PYTHONPATH`.
- **Inference:** a **subprocess** call to DiffDock's `inference.py` (`--protein_path`, `--ligand`
  SMILES, `--out_dir`, `--inference_steps`, `--samples_per_complex`, `--no_final_step_noise`).
  Weights (`/data/weights`, GitHub release v1.1) + ESM2 cache (`/data/hf_cache`,
  `facebook/esm2_t33_650M_UR50D`) live on the PVC, gated. `cwd=/home/appuser/DiffDock`.
- **Endpoint:** `POST /v1/dock` {protein_pdb, ligand_smiles, num_poses?, inference_steps?} →
  {poses:[{rank, confidence, sdf}]}. Body takes PDB + SMILES directly (no `model`/variant collision).
- **Known cosmetic gap:** this DiffDock-L build's SDF filenames don't encode `confidence-<n>`, so the
  parser falls back to `confidence=0.0`. Poses ARE ranked (rank1..N) by DiffDock's internal score;
  the numeric confidence just isn't surfaced from the filename. Follow-up: parse confidence from the
  SDF `$<confidence>` tag or the confidence log instead.

## Deployment (standardized)
- **Pattern:** ConfigMap `diffdock-server` (server.py embedded) mounted at `/server`; initContainer
  (python:3.11-slim) installs pylibs39 + downloads weights + caches ESM2; main container
  (`rbgcsail/diffdock:v1.1.3`) runs `<conda-python> /server/server.py`. `/health` probes.
- **PVC:** standalone `pvc.yaml`, name `diffdock` (was `diffdock-data`), RWX `nfs-models`.
- **GPU:** 1× L40S HAMi slice (`gpumem 16384`); fp32; nodeSelector `gpu=on`. Knative `timeout: 600`.
- **Scale-to-zero:** `minReplicas: 0`, no stop, 15m idle retention. Cold start ~3-6 min (image pull +
  first dock runs the full CLI).
- **Card:** v2 Template B (`schema_version: 2`), id `diffdock` (was `diffdock-l` — now id = ISVC name).

## Files
- `details.yaml` (v2, `diffdock-details`) · `inferenceservice.yaml` (ConfigMap `diffdock-server` + ISVC) ·
  `pvc.yaml` (`diffdock`) · `test.py` + `test_protein.pdb` (crambin/1CRN fixture) · `README.md`.

## Notes
- The Python executable is located at runtime (micromamba `/home/appuser/micromamba/envs/diffdock/...`,
  falling back to conda). Verify on each deploy if the image's env path changes.
