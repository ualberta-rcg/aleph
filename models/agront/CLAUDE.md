# agront Notes

## Purpose
AgroNT (InstaDeepAI) 1B plant-genome DNA language model. Mean-pooled 1500-dim
embeddings from plant DNA via `/v1/embeddings` and `/v1/science/predict`.

## Runtime
- Custom FastAPI server (ConfigMap `agront-server`), venv-on-PVC, GPU.
- `model_id = InstaDeepAI/agro-nucleotide-transformer-1b`; loads from `/data/model`.
- cu121 torch, `transformers==4.46.3`, sentencepiece.

## Migration changes vs 232 (significant)
- 232 used `RawDeployment` + GPU-Operator nodeSelector `nvidia.com/gpu.product` and
  downloaded ~4GB to ephemeral `/tmp` every cold start.
- Converted to standard 230 pattern: Knative scale-to-zero, **PVC venv + weights**,
  HAMi `nodeSelector gpu: "on"` + `nvidia.com/gpu: 1` + `nvidia.com/gpumem: 8192`.
- HF token via `secretKeyRef`. Server now reads `MODEL_DIR=/data/model`.

## Key fact
- **Embedding dim is 1500** (the old card said 1280 — wrong). Verified from live output.

## Resources
- GPU 1 slice, gpumem 8192 MiB. CPU 2/4, mem 6Gi/12Gi. PVC `agront-data` 20Gi.

## Validation
See [TEST.md](TEST.md). dim=1500 on both endpoints.
