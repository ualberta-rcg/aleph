# ligandmpnn — Ligand-Aware Protein Sequence Design

`ligandmpnn` serves **LigandMPNN** (Baker Lab / UW, dauparas/LigandMPNN) — designs amino-acid
sequences for a given protein backbone (PDB), extending ProteinMPNN with ligand awareness (for drug
design). **CPU-capable**. Served via a **subprocess** call to the LigandMPNN CLI (`run.py`).

- **Source:** https://github.com/dauparas/LigandMPNN (weights from the IPD server)
- **License:** MIT
- **Framework:** LigandMPNN CLI + torch (CPU)

## API

`POST /v1/design`

```json
{
  "model": "ligandmpnn",
  "pdb": "<PDB backbone string>",
  "num_sequences": 2,
  "temperature": 0.1,
  "model_type": "ligand_mpnn"
}
```

Returns `sequences` (`[{header, sequence}]`) and `returncode` (0 = success). `model_type` selects
the checkpoint: `ligand_mpnn` (default) | `protein_mpnn` | `soluble_mpnn` |
`per_residue_label_membrane_mpnn`.

## Deployment

- Custom FastAPI server (`server.py` embedded in the `ligandmpnn-server` ConfigMap, mounted read-only
  at `/app`), run via a persisted venv on the PVC (caduceus pattern).
- initContainer clones LigandMPNN (patches the optional `sc_utils`/openfold import so plain design
  works without it), builds `/data/venv` (CPU torch + prody + ml_collections + dm-tree + scipy), and
  downloads the four checkpoints from the IPD server — all on the PVC, gated.
- **CPU-only** (no GPU request; no `gpu=on` nodeSelector). Knative `timeout: 600` (a design run can be slow).
- Scale-to-zero (`minReplicas: 0`, 15m idle retention). Cold start ~2-4 min.

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=ligandmpnn \
  python3 models/ligandmpnn/test.py
```
Designs 2 sequences for crambin (1CRN, `test_protein.pdb`), asserts valid amino-acid output.
