# chemberta Notes

## Purpose
ChemBERTa (seyonec/ChemBERTa-zinc-base-v1). Mean-pooled 768-dim embeddings of SMILES
strings via `/v1/embeddings`. CPU.

## Runtime
- Custom FastAPI server (embedded ConfigMap), venv-on-PVC. CPU.
- Pinned `torch==2.5.1`, `transformers==4.46.3`. HF token via `secretKeyRef`.

## Migration changes vs 232
- Inline HF token → secretKeyRef; pinned torch/transformers; v2 card
  (`routing.k8s_name: chemberta`, id `chemberta-125m`).

## Validation
See [TEST.md](TEST.md). dim=768.
