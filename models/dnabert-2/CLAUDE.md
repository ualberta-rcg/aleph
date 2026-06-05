# dnabert-2

**Type**: DNA sequence embedding (768-dim)
**Model**: zhihan1996/DNABERT-2-117M (117M)
**Endpoint**: POST /v1/embeddings
**Runtime**: CPU, Python FastAPI, venv on PVC

## Migration notes
- Ported from 232 with existing server.py; HF_TOKEN inline → secretKeyRef.
- StorageClass already nfs-client. PVC: dnabert-2-data (10Gi RWX).
- Added `routing.k8s_name: dnabert-2` to details.yaml.

## Key quirks / fixes
- **Tuple output**: DNABERT-2's custom model returns a `tuple` (not a `ModelOutput`
  object), so `.last_hidden_state` fails. Fixed with:
  ```python
  raw = pt_model(**enc)
  hs = raw.last_hidden_state if hasattr(raw, 'last_hidden_state') else raw[0]
  ```
- `trust_remote_code=True` required (uses custom BertConfig/BertModel).
- `low_cpu_mem_usage=False` needed to avoid meta-device initialization error.
- May need `pad_token_id` patched in config if not set.

## Validation
- POST /v1/embeddings with "ATGCGTACGTTACG" → 768-dim float array. PASS.
- Catalog: id=dnabert-2-117m, type=embedding. PASS.
