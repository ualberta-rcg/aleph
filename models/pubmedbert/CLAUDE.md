# pubmedbert

**Type**: Biomedical text embedding (768-dim)
**Model**: microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract (110M)
**Endpoint**: POST /v1/embeddings
**Runtime**: CPU, Python FastAPI, venv on PVC

## Migration notes
- 232 source was a stub (card only, no server.py/ISVC). Built fresh from the
  biomedbert pattern (same standard HF embedding server template).
- `tier: planned` → `production`; removed "NOTE: stub" from description.
- PVC: pubmedbert-data (5Gi RWX, nfs-client). HF_TOKEN secretKeyRef.

## Key quirks
- Pre-trained from scratch on PubMed abstracts only (no Wikipedia/books), resulting
  in a fully biomedical vocabulary. Outperforms BioBERT on domain-specific tasks.
- Gateway routes by card `id: "pubmedbert"`, server reports `MODEL_NAME: pubmedbert-110m`.
  Use `model: "pubmedbert"` in requests, response shows `pubmedbert-110m`.

## Validation
- POST /v1/embeddings with "BRCA1 mutation increases cancer risk" → 768-dim embedding. PASS.
- Catalog: id=pubmedbert, type=embedding. PASS.
- **Embeddings pass (2026-06-19):** 10-check battery via the gateway — **8 PASS / 2 EXP / 0 FAIL**
  (dim 768, batch, distinctness cos 0.93, truncation, guardrails, catalog). Card rewritten to v2
  Template C; `kustomization.yaml` dropped. Run:
  `cat models/pubmedbert/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -`.
