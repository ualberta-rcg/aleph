# ligandmpnn — Ligand-Aware Protein Sequence Design (LigandMPNN)

## Source
- GitHub: https://github.com/dauparas/LigandMPNN (weights from the IPD server, files.ipd.uw.edu)
- License: MIT
- Architecture: ProteinMPNN + ligand context, ~1.7M params, fp32; CPU

## Serving contract (research 2026-06-27)
- **Install:** clone LigandMPNN → `/data/repo`; venv with **CPU** torch + `prody` + `ml_collections` +
  `dm-tree` + `scipy` + fastapi/uvicorn. The init **patches `run.py`'s `sc_utils` import to optional**
  (it pulls openfold → a fragile dep chain unused for plain sequence design).
- **Weights:** 4 checkpoints from `files.ipd.uw.edu/pub/ligandmpnn/` → `/data/model_params`.
  **Note:** `ligandmpnn_per_residue_label_membrane_mpnn_v_32_005_25.pt` 404s on the IPD server
  (non-fatal — the other 3: ligand_mpnn, protein_mpnn, soluble_mpnn download fine).
- **Inference:** **subprocess** to `run.py` (`--pdb_path`, `--out_folder`, `--batch_size`,
  `--temperature`, `--seed`, `--model_type`, `--checkpoint_<type>`). Output parsed from
  `out_dir/seqs/input.fa`. `PYTHONPATH=/data/repo`.
- **Endpoint:** `POST /v1/design` {pdb, num_sequences?, temperature?, model_type?, seed?} →
  {sequences:[{header,sequence}], model_type, returncode}. **No `model` echo field** (server returns
  model_type/returncode instead).
- CPU-only — no GPU, no `gpu=on` nodeSelector.

## Deployment (standardized)
- **Pattern:** caduceus — ConfigMap `ligandmpnn-server` (server.py embedded) mounted read-only at
  `/app`; initContainer clones + patches the repo, builds `/data/venv`, downloads checkpoints (gated);
  main container runs `/data/venv/bin/python /app/server.py`. `/health` startup + readiness probes.
- **PVC:** standalone `pvc.yaml`, name `ligandmpnn` (was `ligandmpnn-data`, **RWO→RWX**), 10Gi.
- **Scale-to-zero:** `minReplicas: 0`, 15m idle retention. Knative `timeout: 600`. Cold start ~2-4 min.
- **Card:** v2 Template B (`schema_version: 2`).

## Files
- `details.yaml` (v2, `ligandmpnn-details`) · `inferenceservice.yaml` (ConfigMap + ISVC) ·
  `pvc.yaml` (`ligandmpnn`) · `test.py` + `test_protein.pdb` (crambin/1CRN) · `README.md`.

## Sanity signal
On crambin (1CRN) the top designed sequence recovers the near-native N-terminus
(`TTCCPSIVARSNFNVCRLPGTPEAICATYT…` ≈ crambin) — strong evidence the design pipeline is correct.
