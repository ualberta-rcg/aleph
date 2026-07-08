# DINOv3 ViT-L/16 — Visual Embedding Service

1024-dim self-supervised image embeddings via Meta's DINOv3 ViT-Large/16 (303M params).
Send a base64 image, get back a 1024-dim CLS-token embedding for similarity/retrieval.

## Usage
```bash
curl -s https://inference.vulcan.alliancecan.ca/v1/science/embed \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"dinov3-vitl16","image":"<base64>"}'
```

**HF**: [facebook/dinov3-vitl16-pretrain-lvd1689m](https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m)
