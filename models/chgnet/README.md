# chgnet — CHGNet Universal NN Potential (with magnetic moments)

`chgnet` serves **CHGNet** (Charge-Enhanced Graph Neural Network, UC Berkeley), a universal graph
neural-network force field trained on Materials Project DFT. **Unique among the force fields here**
for predicting **magnetic moments** and **charge distribution** alongside energy/forces/stress —
useful for battery and magnetic-materials research.

- **Source:** https://github.com/CederGroupHub/chgnet (pip package, bundled pretrained weights; the
  HF repo was removed)
- **License:** MIT
- **Framework:** `chgnet==0.3.8` + pymatgen + ASE + PyTorch (CUDA 12.6)

## API

`POST /v1/science/energy` (same endpoint as `mace-mp-0`)

```json
{
  "model": "chgnet",
  "structure": {
    "elements": ["Na", "Cl"],
    "positions": [[0,0,0],[2.82,2.82,2.82]],
    "cell": [[5.64,0,0],[0,5.64,0],[0,0,5.64]],
    "pbc": [true, true, true]
  }
}
```

Returns `energy_eV` (+ `energy_eV_per_atom`), `forces_eV_per_A` (`[n_atoms][3]`), `stress_GPa`
(Voigt), and `magmom_muB` (per-atom magnetic moments — CHGNet-unique). A large cubic box is
synthesized automatically for molecules (no `cell`).

## Deployment

- Custom FastAPI server (`server.py` embedded in the `chgnet-server` ConfigMap, mounted at `/app`),
  run via a persisted venv on the PVC (caduceus pattern).
- initContainer builds `/data/venv` (**pinned `chgnet==0.3.8`** — 0.4.x removes the
  `atom_features_type` kwarg the bundled graph converter still passes) and best-effort caches the
  checkpoint (HF repo gone → server falls back to `chgnet.load()` bundled weights, non-fatal).
- 1× L40S HAMi slice (`gpumem 8192`); float32; CPU fallback. nodeSelector `gpu=on`.
- Scale-to-zero (`minReplicas: 0`, 15m idle retention).

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=chgnet \
  python3 models/chgnet/test.py
```
Wakes the model, predicts a NaCl cell, asserts energy/forces shape + sanity.
