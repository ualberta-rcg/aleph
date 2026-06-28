# diffdock — DiffDock-L Protein-Ligand Docking

`diffdock` serves **DiffDock-L** (gcorso/DiffDock v1.1.3), a diffusion-based generative model for
protein-ligand docking. Given a protein structure (PDB) + a small molecule (SMILES), it predicts
docked 3D poses with confidence scores. GPU required.

- **Source:** https://github.com/gcorso/DiffDock (image `rbgcsail/diffdock:v1.1.3`)
- **License:** MIT
- **Framework:** DiffDock (diffusion score + confidence models) + ESM-2 + torch-geometric, invoked
  via a **subprocess** call to the DiffDock CLI (`inference.py`)

## API

`POST /v1/dock`

```json
{
  "model": "diffdock",
  "protein_pdb": "<PDB string>",
  "ligand_smiles": "CC(=O)Oc1ccccc1C(=O)O",
  "num_poses": 10,
  "inference_steps": 20
}
```

Returns `poses[]` — each `{rank, confidence, sdf}` (SDF-format docked ligand).

## Deployment

- Custom FastAPI server (`server.py` embedded in the `diffdock-server` ConfigMap, mounted at
  `/server`) running on the **`rbgcsail/diffdock:v1.1.3`** image (conda env with DiffDock + rdkit +
  ESM-2 + torch-geometric pre-built). Server deps (fastapi/uvicorn, pinned for Python 3.9 +
  `click<8.2`) are injected via `PYTHONPATH=/data/pylibs39`.
- initContainer installs those server deps to `/data/pylibs39`, downloads the DiffDock-L weights
  (GitHub release), and pre-caches ESM2 (`facebook/esm2_t33_650M_UR50D`) — all on the PVC, gated.
- 1× L40S HAMi slice (`gpumem 16384`); fp32; nodeSelector `gpu=on`. Knative `timeout: 600` (a dock
  run is slow).
- Scale-to-zero (`minReplicas: 0`, 15m idle retention). Cold start ~3-6 min.

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=diffdock \
  python3 models/diffdock/test.py
```
Docks **aspirin** into **crambin (1CRN)** (read from `test_protein.pdb`), asserts ranked SDF poses.
