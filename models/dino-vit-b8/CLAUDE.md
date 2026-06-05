# dino-vit-b8

**Type**: Vision embedding (DINO ViT-B/8)
**Endpoint**: POST /v1/vision/embed
**Runtime**: CPU, venv on PVC

## Migration notes
- Ported from 232. Already Knative + scale-to-zero + nfs-client PVC.
- Only change: added `routing.k8s_name: dino-vit-b8` to details.yaml.

## Validation
- POST /v1/vision/embed with 1×1 white PNG → float array embedding. PASS.
- Catalog: id=dino-vit-b8, type=embed, endpoint=/v1/vision/embed. PASS.
