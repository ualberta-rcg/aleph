# DiffDock-L -- Model Context

## What This Model Does

DiffDock-L (gcorso/DiffDock v1.1.3) is a diffusion-based generative model for protein-ligand docking. Given a protein structure (PDB format) and a small molecule (SMILES string), it predicts 3D docked poses with confidence scores. Uses score model + confidence model architecture. Runs via subprocess call to DiffDock's `inference.py` inside the official `rbgcsail/diffdock` Docker image. Returns ranked SDF poses with confidence values. MIT license.

## Source Repo

**GitHub**: [gcorso/DiffDock](https://github.com/gcorso/DiffDock)

- **Docker image**: `rbgcsail/diffdock:v1.1.3` (includes rdkit, ESM-2, torch-geometric)
- **Weights**: Downloaded from GitHub releases (`diffdock_models.zip`)
- **License**: MIT
- **ESM-2 dependency**: Pre-caches `facebook/esm2_t33_650M_UR50D` for protein embeddings

## How The Server Works

- **Pattern**: Custom FastAPI + subprocess call to DiffDock CLI
- **Container**: `rbgcsail/diffdock:v1.1.3` with Python from micromamba env
- **Init container** (`python:3.11-slim`): Installs FastAPI server deps to `/data/pylibs39` (Python 3.9 compatible), downloads DiffDock-L weights, pre-caches ESM-2
- **ConfigMap**: Server code embedded as `diffdock-server` ConfigMap, mounted at `/server/`
- **PVC**: `diffdock-data` (20Gi, NFS) -- stores weights, pylibs, HF/torch caches
- **Health**: `/health` checks if weights directory is populated
- **GPU**: 1x L40S-SHARED (time-sliced), fp32 inference
- **Startup**: ~3-4 minutes (model loading)
- **Inference**: Writes protein PDB + ligand SMILES to temp dir, calls `inference.py` via subprocess, parses output SDF files with rank/confidence from filenames

## Our Config vs Source Recommendations

| Aspect | Source | Our Config | Notes |
|--------|--------|-----------|-------|
| Inference method | Python API | Subprocess CLI | Works around env conflicts |
| Batch size | Variable | 5 | Reasonable for single requests |
| Inference steps | 20 default | 20 default | Matches source |
| Num poses | Variable | 10 default | Good for exploration |
| Final step noise | Optional | Disabled (`--no_final_step_noise`) | Cleaner poses |

## Gateway Integration

- **ISVC name**: `diffdock` (maps to API id `diffdock-l`)
- **MODEL_TYPE**: dock
- **KSERVE_CUSTOM_MODELS**: yes -- uses `/v1/` prefix
- **GPU_MODELS**: yes
- **CONTEXT_WINDOWS**: 0 (not applicable)
- **Scale-to-zero**: minReplicas=0, scaleTarget=3, 900s retention
- **Custom health probe**: yes (in `_CUSTOM_HEALTH_MODELS`)
- **Startup time estimate**: 3-4 minutes

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/diffdock/

# Force update
kubectl apply --server-side --force-conflicts -k models/diffdock/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=diffdock

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=diffdock -c kserve-container -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/dock \
  -H "Content-Type: application/json" \
  -d '{"protein_pdb":"ATOM    1  CA  ALA A   1       1.000   2.000   3.000","ligand_smiles":"CC(=O)Oc1ccccc1C(=O)O","num_poses":5}'
```

## Known Issues / Optimization Opportunities

1. **Server deps version-locked**: FastAPI/uvicorn pinned (0.103.2/0.23.2) for Python 3.9 compat inside DiffDock image. This is fragile.

2. **Subprocess inference**: Calling DiffDock via subprocess is slower and more fragile than direct Python API. Done because the conda env in the DiffDock image has different Python version than what FastAPI needs.

3. **Python discovery**: Complex fallback chain to find the correct Python executable inside the DiffDock image (micromamba path). Could break if image updates change the path.

4. **fp32 on GPU**: DiffDock runs in fp32. Could potentially use fp16 for speed.

5. **600s timeout**: Long timeout needed for large proteins. Could be configurable.

6. **Init container idempotent**: Yes -- checks for pylibs39/fastapi, weights directory, and ESM-2 cache marker before installing/downloading.

7. **No readOnly mount**: PVC is mounted read-write for main container (needed for HF/torch caches at runtime). Could pre-cache everything in init and use readOnly.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap (server.py) + ISVC spec |
| `kustomization.yaml` | Kustomize resources + configMapGenerator |
| `pvc.yaml` | Dedicated PVC (diffdock-data, 20Gi NFS) |
| `server.py` | Extracted server code (actual code lives in ConfigMap via kustomize configMapGenerator) |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml, server.py), update details.yaml to match.**
