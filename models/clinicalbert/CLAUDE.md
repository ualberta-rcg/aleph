# clinicalbert Notes

## Purpose
Bio_ClinicalBERT (emilyalsentzer). Mean-pooled 768-dim clinical-text embeddings via
`/v1/embeddings`. CPU.

## Runtime
- Custom FastAPI server (embedded ConfigMap), venv-on-PVC. CPU.
- Pinned `torch==2.5.1`, `transformers==4.46.3`. HF token via `secretKeyRef`.

## Migration changes vs 232
- Inline HF token → secretKeyRef; pinned torch/transformers; v2 card
  (`routing.k8s_name: clinicalbert`, id `clinicalbert-110m`).

## Validation
See [TEST.md](TEST.md). dim=768.
