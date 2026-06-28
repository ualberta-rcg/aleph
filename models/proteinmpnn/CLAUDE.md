# proteinmpnn — Protein Sequence Design (ProteinMPNN)

## Source
- GitHub: https://github.com/dauparas/ProteinMPNN (weights `v_48_020.pt`)
- License: MIT
- Architecture: ProteinMPNN VAE; tiny; torch cu121; GPU (small HAMi slice)

## Serving contract (research 2026-06-27)
- **Install:** torch (cu121) + numpy + fastapi/uvicorn/huggingface_hub. Persisted venv on PVC.
  The ProteinMPNN model code ships in this dir (`pmpnn_run.py`, `pmpnn_utils.py`), loaded in-process.
- **Weights:** `v_48_020.pt` from the ProteinMPNN GitHub raw → `/data/weights`.
- **API:** `POST /v1/design` {pdb, num_sequences?, temperature?, chains_to_design?, omit_AAs?} →
  {sequences:[{sequence, score, global_score, seq_recovery}], num_sequences, native_sequence,
  chains_designed}. **In-process** (not subprocess).
- The `model` field is the gateway routing id; the server returns `model: "proteinmpnn"`.

## Deployment (standardized)
- **Pattern:** caduceus — ConfigMap `proteinmpnn-server` (server.py embedded) mounted read-only at
  `/app`; initContainer builds `/data/venv` + downloads weights (gated); main container runs the venv
  python. `/health` probes.
- **PVC:** standalone `pvc.yaml`, name `proteinmpnn` (was `proteinmpnn-data`), RWX `nfs-models` 15Gi.
- **GPU:** 1× L40S HAMi slice (`gpumem 4096`); nodeSelector `gpu=on`.
- **Scale-to-zero:** `minReplicas: 0`, 15m idle retention.
- **Card:** already v2 (`schema_version: 2`).

## Files
- `details.yaml` (v2, `proteinmpnn-details`) · `inferenceservice.yaml` (ConfigMap + ISVC) ·
  `pvc.yaml` (`proteinmpnn`) · `pmpnn_run.py` + `pmpnn_utils.py` (ProteinMPNN model code) ·
  `test.py` + `test_protein.pdb` (crambin/1CRN) · `README.md`.
