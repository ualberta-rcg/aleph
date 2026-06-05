# biomedbert Notes

## Purpose
Microsoft BiomedBERT (PubMedBERT-base-uncased-abstract), 110M. Mean-pooled 768-dim
biomedical text embeddings via `/v1/embeddings`.

## Runtime
- Custom FastAPI server (ConfigMap `biomedbert-server`), venv-on-PVC pattern.
- CPU-only (110M) — fast enough without a GPU slice.
- Pinned `torch==2.5.1` (CPU), `transformers==4.46.3` for reproducibility.
- HF token via `secretKeyRef: hf-token` (download step).

## Migration changes vs 232
- Inline HF token → `secretKeyRef`.
- Pinned torch/transformers (were unpinned).
- Card converted to v2 schema; added `routing.k8s_name: biomedbert` (model id is
  `biomedbert-110m`, ISVC name is `biomedbert`).

## Resources
- CPU req/limit 2/4; mem 2Gi/4Gi. PVC `biomedbert-data` 5Gi (RWX, nfs-client).

## Validation
See [TEST.md](TEST.md). Embeddings dim=768 verified.
