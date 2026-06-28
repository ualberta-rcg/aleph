# mace-mp — MACE-MP-0 Universal Interatomic Potential

`mace-mp` serves the **MACE-MP-0** universal machine-learning interatomic potential
(`ACEsuit/mace-mp-0`), trained on the Materials Project and covering **89 elements** via the
equivariant MACE architecture. Three model sizes are bundled: **small** (~2M), **medium** (~10M,
default), **large** (~30M). float64 precision.

- **Source:** https://huggingface.co/ACEsuit/mace-mp-0
- **License:** MIT
- **Framework:** `mace-torch` + ASE + PyTorch (CUDA 12.6)

## API

`POST /v1/science/predict`

```json
{
  "elements": ["Si", "Si"],
  "positions": [[0,0,0],[1.35,1.35,1.35]],
  "lattice":  [[2.7,2.7,0],[2.7,0,2.7],[0,2.7,2.7]],
  "model": "medium"
}
```

Returns `energy_eV`, `forces_eV_per_Ang` (`[n_atoms][3]`), and `stress_eV_per_Ang3` (Voigt 6,
periodic only). `lattice` may be omitted for molecules; `model` selects the variant.

## Deployment

- Custom FastAPI server (`server.py` embedded in the `mace-mp-server` ConfigMap, mounted at `/app`,
  read-only data mount), run via a persisted venv on the PVC (caduceus pattern).
- initContainer builds `/data/venv` (torch cu126 + `mace-torch>=0.3` + ase) and downloads the three
  MACE-MP-0 weight files to `/data/models`, both gated by sentinels → fast cold starts.
- 1× L40S HAMi slice (`gpumem 10240`); float64; CPU fallback. nodeSelector `gpu=on`.
- Scale-to-zero (`minReplicas: 0`, 15m idle retention).

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=mace-mp \
  python3 models/mace-mp/test.py
```
Wakes the model, predicts a Si cell (medium variant), asserts energy/forces/stress shape + sanity.
