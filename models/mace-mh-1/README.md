# MACE-MH-1 — Multi-Head Foundation Force Field

MACE-MH-1 (`mace-foundations/mace-mh-1`) is a multi-head foundation machine-learning interatomic
potential (MLIP) covering **89 elements** across **7 specialized heads**, each tuned to a different
chemistry: `omat_pbe` (inorganic solids), `omol` (molecules), `spice_wB97M` (SPICE bio/organo),
`rgd1_b3lyp` (RGD1 reactions), `oc20_usemppbe` (catalysis), `matpes_r2scan` (Materials Project PES).
Equivariant MACE architecture, float64 precision.

- **Source:** https://huggingface.co/mace-foundations/mace-mh-1
- **License:** ASL (academic / non-commercial)
- **Framework:** `mace-torch` + ASE + PyTorch (CUDA 12.6)

## API

`POST /v1/science/predict`

```json
{
  "elements": ["Cu", "Cu", "Cu", "Cu"],
  "positions": [[0,0,0],[1.8,1.8,0],[1.8,0,1.8],[0,1.8,1.8]],
  "lattice":  [[3.6,0,0],[0,3.6,0],[0,0,3.6]],
  "head": "omat_pbe"
}
```

Returns `energy_eV`, `forces_eV_per_Ang` (`[n_atoms][3]`), and `stress_eV_per_Ang3` (Voigt 6, periodic
only). `lattice` may be omitted for molecules. Pass `demo: true` for a built-in Cu test structure.

## Deployment

- Custom FastAPI server (`server.py` embedded in the `mace-mh-1-server` ConfigMap, mounted at `/app`),
  run via a persisted venv on the PVC (caduceus pattern).
- initContainer builds `/data/venv` (torch cu126 + `mace-torch>=0.3` + ase + fastapi/uvicorn) and
  downloads `mace-mh-1.model` to `/data/models`, both gated by sentinels → fast cold starts.
- 1× L40S HAMi slice (`gpumem 16384`); float64; falls back to CPU if no GPU.
- Scale-to-zero (`minReplicas: 0`, 15m idle retention).

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=mace-mh-1 \
  python3 models/mace-mh-1/test.py
```
Wakes the model, predicts a Cu cell, and asserts the energy/forces/stress shape + sanity.
