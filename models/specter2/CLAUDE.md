# specter2

**Type**: Scientific paper embedding (768-dim)
**Model**: allenai/specter2_base (110M)
**Endpoint**: POST /v1/embeddings
**Runtime**: CPU, Python FastAPI, venv on PVC

## Migration notes
- Ported from 232 with existing server.py embedding pattern.
- Only change: `HF_TOKEN` inline → `secretKeyRef: hf-token`.
- StorageClass already `nfs-models`. PVC: `specter2-data` (5Gi RWX).
- Added `routing.k8s_name: specter2` to details.yaml.

## Key quirks
- SPECTER2 is designed for scientific paper retrieval (title+abstract as input).
- Mean-pooling over attention-masked last_hidden_state.
- Works well for document similarity, paper search, citation recommendation.

## Validation
- POST /v1/embeddings → 768-dim float array. PASS.
- Catalog: id=specter2-110m, type=embedding. PASS.
