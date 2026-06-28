# mace-mp-0 — MACE-MP-0 Force Field (CPU, `/v1/science/energy`)

`mace-mp-0` serves the **MACE-MP-0** universal force field (Cambridge/DeepMind) via the mace-torch
`mace_mp()` convenience loader — the **medium** variant, the GitHub-released
`2023-12-03-mace-128-L1_epoch-199` checkpoint. Predicts energy, per-atom forces, and stress from an
atomic structure. **CPU-only**, float32. (The companion `mace-mp` service is the GPU
`/v1/science/predict` variant with small/medium/large selection.)

- **Source:** https://github.com/ACEsuit/mace · model: https://github.com/ACEsuit/mace-mp/releases
- **License:** MIT
- **Framework:** `mace-torch` (`mace_mp`) + ASE + PyTorch (CPU)

## API

`POST /v1/science/energy`

```json
{
  "model": "mace-mp-0",
  "structure": {
    "elements": ["Si", "Si"],
    "positions": [[0,0,0],[1.35,1.35,1.35]],
    "cell": [[2.7,2.7,0],[2.7,0,2.7],[0,2.7,2.7]],
    "pbc": [true, true, true]
  }
}
```

Returns `energy_eV`, `forces_eV_A` (`[n_atoms][3]`), and `stress_eV_A3` (Voigt 6, periodic only —
`null` for molecules). Omit `cell`/`pbc` for a molecule.

## Deployment

- Custom FastAPI server (`server.py` embedded in the `mace-mp-0-server` ConfigMap, mounted read-only
  at `/app`), run via a persisted venv on the PVC (caduceus pattern).
- initContainer builds `/data/venv` (CPU torch + `mace-torch` + ase) and caches the medium model to
  `/data/mace-models` (so cold starts don't re-download the 42 MB checkpoint), both gated.
- **CPU-only** (no GPU request); runs on any worker. nodeSelector `gpu=on` NOT set.
- Scale-to-zero (`minReplicas: 0`, 15m idle retention).

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=mace-mp-0 \
  python3 models/mace-mp-0/test.py
```
Wakes the model, predicts a Si cell, asserts energy/forces/stress shape + sanity.
