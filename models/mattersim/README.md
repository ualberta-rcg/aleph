# mattersim — Microsoft MatterSim Universal Atomistic Force Field

`mattersim` serves **MatterSim** (Microsoft Research, arXiv 2405.04967), a universal deep-learning
atomistic force field trained across elements, temperatures, and pressures. Predicts energy, per-atom
forces, and stress, and exposes a **structure relaxation** endpoint (BFGS).

- **Source:** https://huggingface.co/microsoft/mattersim
- **License:** MIT
- **Framework:** `mattersim` (MatterSimCalculator) + ASE + torch + torch_geometric (CUDA 12.6)

## API

`POST /v1/science/predict`

```json
{
  "model": "mattersim",
  "elements": ["Si", "Si"],
  "positions": [[0,0,0],[1.35,1.35,1.35]],
  "lattice": [[2.7,2.7,0],[2.7,0,2.7],[0,2.7,2.7]]
}
```

Returns `energy_ev`, `energy_per_atom_ev`, `forces_ev_per_angstrom` (`[n_atoms][3]`), and
`stress_ev_per_angstrom3` + `stress_gpa` (periodic only). The `model` field is the gateway routing
id; the server ignores it otherwise.

`POST /v1/science/relax` — `{elements, positions, lattice, fmax?(0.05), steps?(200)}` → BFGS-relaxed
structure (`converged`, `steps`, `relaxed_positions`, `relaxed_cell`, `energy_ev`).

## Deployment

- Custom FastAPI server (`server.py` embedded in the `mattersim-server` ConfigMap, mounted read-only
  at `/app`), run via a persisted venv on the PVC (caduceus pattern).
- initContainer builds `/data/venv` (torch cu126 + `torch_geometric` + `mattersim` + ase; `git` +
  `build-essential` for compiles) and pre-caches the MatterSim checkpoint to `/data/torch_cache`,
  both gated → fast cold starts.
- 1× L40S HAMi slice (`gpumem 10240`); float32; CPU fallback. nodeSelector `gpu=on`.
- Scale-to-zero (`minReplicas: 0`, 15m idle retention). Cold start ~2-4 min.

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=mattersim \
  python3 models/mattersim/test.py
```
Wakes the model, predicts a Si cell (energy/forces/stress), and exercises the relax endpoint.
