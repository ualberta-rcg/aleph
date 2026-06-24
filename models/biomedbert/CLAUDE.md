# biomedbert Notes

## Purpose
Microsoft BiomedBERT (microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract), 110M. Mean-pooled 768-dim
biomedical text embeddings via `/v1/embeddings`.

## Runtime
- Custom FastAPI server (ConfigMap `biomedbert-server`), venv-on-PVC pattern.
- CPU-only (110M) — fast enough without a GPU slice.
- Pinned `torch==2.5.1` (CPU), `transformers==4.46.3` for reproducibility.
- HF token via `secretKeyRef: hf-token` (download step).

## Migration changes
- Inline HF token → `secretKeyRef`.
- Pinned torch/transformers (were unpinned).
- Card converted to v2 schema; added `routing.k8s_name: biomedbert` (model id is
  `biomedbert-110m`, ISVC name is `biomedbert`).

## Resources
- CPU req/limit 2/4; mem 2Gi/4Gi. PVC `biomedbert-data` 5Gi (RWX, nfs-models).

## Validation
- **Embeddings pass (2026-06-19):** 10-check battery via the gateway — **8 PASS / 2 EXP / 0 FAIL**
  (dim 768, batch, distinctness cos 0.79, truncation, guardrails, catalog). Card: fixed a
  PubMedBERT→BiomedBERT description copy-paste error. Run externally:
  `GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/biomedbert/test.py` (or in-pod:
  `cat models/biomedbert/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -`).
