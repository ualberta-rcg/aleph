# dino-vit-b8 — DINO ViT-B/8 visual embeddings

DINO ViT-Base/8 (Meta, 86M) — self-supervised Vision Transformer. Patch size 8; **768-dim
embedding** of a base64 image (resized 224×224, ImageNet-normalized). Served via ONNX Runtime (CPU).

## Source
- HuggingFace: https://huggingface.co/onnx-community/vit_base_patch8_224.dino-ONNX
- License: Apache-2.0

## API — `POST /v1/science/embed` (NON-OpenAI domain endpoint, primary)
Image input → does NOT expose OpenAI `/v1/embeddings`. `/v1/vision/embed` kept as a secondary alias.
Body needs `"model": "dino-vit-b8"`:
- `{"model":"dino-vit-b8", "image":"<base64 PNG/JPEG>"}` → 768-dim (data-url prefix optional)
- Returns `{"model":"dino-vit-b8", "task":"embed", "embedding":..., "embeddings":...(alias), "dim":768}`.

## Deployment
- **CPU-only** (ONNX Runtime, CPUExecutionProvider, ~30s cold start).
- **PVC**: `dino-vit-b8-data` — **ReadWriteMany**, nfs-models (already RWX, `pvc.yaml`).
- **Venv-on-PVC**: `/data/venv` (onnxruntime + Pillow + numpy, guarded).
- **Scale-to-zero**: minReplicas 0, 15m retention.

## Key files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC
- `details.yaml` — v2 card (Template C)
- `pvc.yaml` — RWX PVC
- `test.py` — 6-case gateway battery (dim 768 / non-zero / distinctness / deterministic / echo / malformed); generates a pure-stdlib PNG (no PIL in the gateway pod)

## Notes
- ONNX opset 17, input 224×224, ImageNet mean/std normalization, intra_op_num_threads=4.
- Input is base64 (the server handles data-url `data:image/png;base64,...` prefix stripping).

## Update reminder
- Watch onnx-community for fp16/quantized variants.

## HF / upstream I/O reference
- Source: https://huggingface.co/onnx-community/vit_base_patch8_224.dino-ONNX
- Runtime mapping used here: base64 image -> embedding (dim 768) on `/v1/vision/embed` (alias `/v1/science/embed`).
