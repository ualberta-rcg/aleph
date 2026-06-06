# diffdock — Test Report

Cluster 230, gateway ClusterIP `http://10.43.79.101:80`. Type: dock (DiffDock-L, GPU). id `diffdock-l`.

## Status: FIXED + verified 2026-06-06
Three issues: (1) click 8.2+ installed into Python 3.9 env (SyntaxError on match-syntax);
(2) ligand passed as `.smi` file path but DiffDock expects SMILES string or .mol2/.sdf/.pdbqt;
(3) confidence regex grabbed trailing `.` from `.sdf` extension (`-3.97.` → float error).

## Verified this pass

### POST /v1/dock — PASS
```bash
GW=http://10.43.79.101
# minimal: protein PDB string + ligand SMILES
curl -s -X POST $GW/v1/dock -H 'Content-Type: application/json' \
  -d '{"model":"diffdock-l","protein_pdb":"<PDB ATOM records>","ligand_smiles":"CC(=O)Oc1ccccc1C(=O)O","num_poses":3}'
```
Verified on crambin (1CRN, 327 ATOMs) + aspirin: **11 ranked poses** with confidence
scores and SDF content. ~60s inference. PASS.

## Key fixes
- Init: pin `click<8.2`, reinstall pylibs39 with `.deps-v2` sentinel.
- `--ligand` now receives SMILES string directly (not a `.smi` file path).
- Confidence regex: `confidence(-?\d+(?:\.\d+)?)` (no trailing dot).

## Card parity
id=diffdock-l, type=dock, gpu=true, status=production. Endpoint: `/v1/dock`.
Needs real protein structure (not degenerate 2-residue peptide — graph has no edges).
