# esmfold — Protein Structure Prediction (ESMfold)

## Source
- HuggingFace: https://huggingface.co/facebook/esmfold_v1
- License: MIT
- Architecture: ESM-2 backbone (~690M params) + folding head; fp32; max 1022 residues

## Serving contract (research 2026-06-27)
- **Install:** `numpy<2` (numpy 2.x breaks transformers' `protein.py` format specs) + `torch` +
  `transformers` + `protobuf` + `fastapi`/`uvicorn`/`huggingface_hub`. Persisted venv on the PVC
  (gated by `/data/venv/bin`).
- **Weights:** `facebook/esmfold_v1` via `snapshot_download` → `/data/model` (~9 GiB). Public.
- **API:** `POST /v1/structure` {sequence} → {pdb (PDB string), plddt (0-100)}. `EsmForProteinFolding`
  + `model.output_to_pdb()`. transformers 5.x still ships the class (2 benign contact_head params
  MISSING on load — expected, they're for contact prediction, not folding).
- **pLDDT:** the raw `output["plddt"]` is a **0-1 fraction**; the server scales it **×100** to the
  standard 0-100 convention (AlphaFold/ESMFold docs). ~75 = good confidence.

## Deployment (standardized)
- **Pattern:** caduceus — ConfigMap `esmfold-server` (server.py embedded) mounted read-only at `/app`;
  initContainer builds `/data/venv` + downloads weights; main container runs
  `/data/venv/bin/python /app/server.py`. `/health` startup + readiness probes (initialDelay generous —
  ESMFold load is slow).
- **PVC:** standalone `pvc.yaml`, name `esmfold` (was `esmfold-data`), RWX `nfs-models` 25Gi.
- **GPU:** 1× L40S HAMi slice (`gpumem 30720`); fp32; nodeSelector `gpu=on`. Memory 16-32 Gi.
- **Scale-to-zero:** `minReplicas: 0`, no stop, 15m idle retention. Cold start ~2-4 min (load +
  first fold compiles many torch ops — slow; a 6-min wake window may miss the very first deploy,
  re-run warm).
- **Card:** v2 Template B (`schema_version: 2`), typed input_map/output_map.

## Server fix applied (2026-06-27)
- `plddt` scaled `×100` (0-1 → 0-100 standard convention).

## Files
- `details.yaml` (v2, `esmfold-details`) · `inferenceservice.yaml` (ConfigMap `esmfold-server` + ISVC) ·
  `pvc.yaml` (`esmfold`) · `test.py` (30-aa ubiquitin fragment → pdb + plddt) · `README.md`.
