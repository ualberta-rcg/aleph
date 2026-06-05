# alphafold2 — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: structure-prediction (GPU/HAMi). id `alphafold2`.

## Scale-up
- First-ever cold start: init installs colabfold + jax(cuda12) + downloads AF2 params
  (~3.8GB) to PVC (guarded by sentinel `.af2-params-ready-v4`). Took ~7 min here.
  Warm restarts skip all of that (venv + params on PVC).
- HAMi: 1 vGPU slice, `nvidia.com/gpumem: 24576`. Pod `3/3 Running`.

## Endpoint test (PASS)

### POST /v1/science/predict (demo peptide, num_recycle=1)
```bash
curl -s -X POST $GW/v1/science/predict --max-time 580 \
  -d '{"model":"alphafold2","demo":true,"num_recycle":1}'
```
→ returned PDB (`pdb_len=64881`), `mean_plddt=51.0`, `inference_s=163.5`. PASS.
- Confirms the full pipeline works: MSA fetched from public api.colabfold.com (egress OK),
  AF2 params loaded from PVC, GPU fold, PDB + per-residue pLDDT parsed.

## Notes / minor
- `ptm` came back `None` — the value isn't always present in colabfold stdout for the
  `_ptm` model at num_recycle=1; pLDDT/PDB are the primary outputs and are correct.
- Real sequences: `{"sequence":"MKT...", "num_recycle":3}` (<=1000 aa). Higher num_recycle
  improves quality but increases time.

## Not applicable
- OpenAI chat / Anthropic / reasoning: N/A (structure prediction).

## Card parity
id=alphafold2, k8s_name=alphafold2, type=structure-prediction, gpu=true,
gpumem 24576, primary `/v1/science/predict`, default num_recycle=3.
