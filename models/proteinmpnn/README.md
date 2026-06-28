# proteinmpnn — Protein Sequence Design (ProteinMPNN)

`proteinmpnn` serves **ProteinMPNN** (dauparas/ProteinMPNN) — designs amino-acid sequences for a
given protein backbone (PDB). A variational autoencoder trained on backbones from the PDB. Runs
**in-process** (not subprocess) on GPU.

- **Source:** https://github.com/dauparas/ProteinMPNN (weights `v_48_020.pt`)
- **License:** MIT
- **Framework:** torch (CUDA 12.1); in-process `ProteinMPNN` model

## API

`POST /v1/design`

```json
{ "model": "proteinmpnn", "pdb": "<PDB string>", "num_sequences": 8, "temperature": 0.1 }
```

Returns `sequences` (`[{sequence, score, global_score, seq_recovery}]`), `num_sequences`, and
`native_sequence`. `seq_recovery` measures how close the design is to the input backbone's native
sequence.

## Deployment

- Custom FastAPI server (`server.py` embedded in the `proteinmpnn-server` ConfigMap, mounted
  read-only at `/app`), run via a persisted venv on the PVC (caduceus pattern). The ProteinMPNN model
  code (`pmpnn_run.py`, `pmpnn_utils.py`) is bundled in the dir.
- initContainer builds `/data/venv` (torch cu121) and downloads the `v_48_020.pt` weights, both
  gated → fast cold starts.
- 1× L40S HAMi slice (`gpumem 4096` — ProteinMPNN is tiny); nodeSelector `gpu=on`.
- Scale-to-zero (`minReplicas: 0`, 15m idle retention).

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=proteinmpnn \
  python3 models/proteinmpnn/test.py
```
Designs 3 sequences for crambin (1CRN, `test_protein.pdb`), asserts valid AA output + seq_recovery.
