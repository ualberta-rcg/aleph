# alphafold2 Notes

## Purpose
AlphaFold2 protein structure prediction via ColabFold (`colabfold_batch`, model
`alphafold2_ptm`). POST a sequence to `/v1/science/predict` → PDB + per-residue pLDDT +
mean pLDDT (+ pTM when available).

## Runtime (heavyweight)
- Custom FastAPI server wrapping the colabfold CLI. GPU (jax cuda12).
- MSA fetched from the public ColabFold API `https://api.colabfold.com` (needs egress).
- AF2 params (~3.8GB) + venv cached on PVC; first cold start ~7 min, warm ~1-2 min.

## Migration changes vs 232 (significant)
- 232 used `RawDeployment` + GPU-Operator nodeSelector + installed `jax[cuda12]` in the
  **main** container on every start.
- Converted to standard 230 pattern: Knative scale-to-zero, HAMi `gpu: "on"` +
  `nvidia.com/gpu: 1` + `nvidia.com/gpumem: 24576`, PVC `storageClassName: nfs-models`.
- Moved the `jax[cuda12]` + fastapi install into the **init** container (guarded by the
  sentinel) so warm restarts don't reinstall. Main container just execs the server.

## Quirks
- Predictions are slow (10s–minutes depending on length/num_recycle). `timeout: 600`.
- `ptm` parsing from colabfold stdout is best-effort (may be None); pLDDT/PDB are primary.
- External dependency on api.colabfold.com for MSA.

## Validation
See [TEST.md](TEST.md). Demo fold returned a valid PDB + pLDDT in ~163s.
