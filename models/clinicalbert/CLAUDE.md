# clinicalbert Notes

## Purpose
Bio_ClinicalBERT (emilyalsentzer). Mean-pooled 768-dim clinical-text embeddings via
`/v1/embeddings`. CPU.

## Runtime
- Custom FastAPI server (embedded ConfigMap), venv-on-PVC. CPU.
- Pinned `torch==2.5.1`, `transformers==4.46.3`. HF token via `secretKeyRef`.

## Migration changes
- Inline HF token → secretKeyRef; pinned torch/transformers; v2 card
  (`routing.k8s_name: clinicalbert`, id `clinicalbert-110m`).

## Validation
See [test.py](test.py). dim=768 (2026-06-19: 8 PASS / 2 EXP / 0 FAIL).
Run externally: `GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/clinicalbert/test.py`.
