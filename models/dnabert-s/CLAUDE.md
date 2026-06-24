# dnabert-s

**Type**: Species-aware DNA embedding (768-dim)
**Model**: zhihan1996/DNABERT-S (117M)
**Endpoints**: POST /v1/embeddings, POST /v1/science/predict
**Runtime**: CPU, Python FastAPI, venv on PVC

## Deployment notes
- Knative scale-to-zero; CPU-only (no GPU nodeSelector); init container builds the
  model cache on a PVC; `HF_HOME` on PVC; `HF_HUB_OFFLINE=1` at runtime; `MODEL_ID`
  env points to `/data/model` (local path).
- `endpoints` is a dict (gateway compat); `/v1/science/predict` alias in server.
- PVC: dnabert-s-data (10Gi RWX, nfs-models).

## Key quirks
- Uses custom BertModel + manifold instance mixup. `trust_remote_code=True` required.
- Server patches `torch._prims_common.check_same_device` to tolerate meta tensors,
  and nullifies `flash_attn_qkvpacked_func` to force CPU attention path.
- Downloads to `/data/model` via `snapshot_download`; MODEL_ID env var points there.

## Validation
- POST /v1/embeddings with "ATGCGTACGTTACG" → 768-dim species-aware embedding. PASS.
- Catalog: id=dnabert-s, type=embedding. PASS.
