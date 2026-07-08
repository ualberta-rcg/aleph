# dinov3-vitl16 Notes

## Purpose
Vision embedding service using DINOv3 ViT-L/16 (Meta AI). 1024-dim CLS-token embeddings
for image similarity, retrieval, clustering. Requested by Steven Tang.

## Runtime
- Image: `python:3.11-slim`; server: custom FastAPI at `/app/server.py`
- Entry: `/data/venv/bin/python /app/server.py`
- API: `POST /v1/science/embed` (or `/v1/vision/embed`), `GET /health`, `GET /v1/models`
- HF: `facebook/dinov3-vitl16-pretrain-lvd1689m` (303M, fp32, safetensors)
- GPU: CPU only (303M model, ~1.2 GB RAM). No GPU resources needed.
- Venv: torch (CPU) + transformers + Pillow + fastapi + uvicorn + huggingface_hub

## Resources
- CPU: 2/4, Memory: 4Gi/8Gi
- GPU: none (CPU inference)
- Storage: 5Gi RWX PVC (`nfs-models`)

## Input/Output
- Input: `{"model": "dinov3-vitl16", "image": "<base64>"}` — base64 JPEG/PNG
- Output: `{"model": "dinov3-vitl16", "embedding": [1024 floats], "dim": 1024}`
- Pooling: CLS token (`last_hidden_state[:, 0, :]`)

## Quirks
- DINOv3 needs recent transformers (supports `dinov3_vit` model type, added ~4.46+)
- Distilled from ViT-7B teacher (arxiv:2508.10104)
- Scale-to-zero; cold start ~1-2 min (venv + weights cached on PVC)
