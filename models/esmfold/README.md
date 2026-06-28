# esmfold — Protein Structure Prediction

`esmfold` serves **ESMfold** (Meta, `facebook/esmfold_v1`) — end-to-end protein structure
prediction directly from an amino-acid sequence. Single-sequence method (no MSA / external DB).
Based on the ESM-2 backbone (~690M params). Returns a PDB-format structure + per-residue pLDDT.
Max **1022 residues**, fp32.

- **Source:** https://huggingface.co/facebook/esmfold_v1
- **License:** MIT
- **Framework:** `transformers` (`EsmForProteinFolding`) + torch (CUDA 12.x)

## API

`POST /v1/structure`

```json
{ "model": "esmfold", "sequence": "MQIFVKTLTGKTITLEVEPSDTIENVKAK" }
```

Returns `pdb` (PDB-format string) and `plddt` (mean per-residue confidence, 0–100).

## Deployment

- Custom FastAPI server (`server.py` embedded in the `esmfold-server` ConfigMap, mounted read-only
  at `/app`), run via a persisted venv on the PVC (caduceus pattern).
- initContainer builds `/data/venv` (**`numpy<2`** — numpy 2.x breaks transformers' `protein.py`
  format specs — + torch + transformers + protobuf) and downloads `facebook/esmfold_v1` to
  `/data/model`, both gated → fast cold starts.
- 1× L40S HAMi slice (`gpumem 30720`); fp32; nodeSelector `gpu=on`. (ESMFold is ~690M.)
- Scale-to-zero (`minReplicas: 0`, 15m idle retention). Cold start ~2-4 min.

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=esmfold \
  python3 models/esmfold/test.py
```
Wakes the model, folds a 30-residue sequence, asserts pdb non-empty + plddt ∈ [0,100].
