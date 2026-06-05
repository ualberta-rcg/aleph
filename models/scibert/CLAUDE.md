# scibert

**Type**: Text embedding (768-dim)
**Model**: allenai/scibert_scivocab_uncased (110M)
**Endpoint**: POST /v1/embeddings
**Runtime**: CPU, Python FastAPI, venv on PVC

## Migration notes
- Ported from 232 with existing server.py embedding pattern already in place.
- Only change: `HF_TOKEN` inline → `secretKeyRef: hf-token`.
- StorageClass already `nfs-client` on 232. PVC: `scibert-data` (5Gi RWX).
- Knative scale-to-zero already set; annotations kept.

## Key quirks
- Uses SciVocab tokenizer (custom SentencePiece). Standard `AutoTokenizer` works.
- Mean-pooling over attention-masked tokens (standard).
- 82% biomedical / 18% CS papers in pre-training corpus.

## Validation
- POST /v1/embeddings → 768-dim float array. PASS.
- Catalog: id=scibert-110m, type=embedding. PASS.
