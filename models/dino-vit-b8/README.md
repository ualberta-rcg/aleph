# DINO ViT-B/8 (onnx-community/vit_base_patch8_224.dino-ONNX)

DINO ViT-Base/8 (Meta AI, 86M) — a self-supervised Vision Transformer trained with no labels via
self-distillation. Patch size 8 (fine-grained); produces a **768-dim embedding** of an image.
Use cases: image similarity, clustering, zero-shot retrieval, copy detection. Served via ONNX
Runtime on CPU.

Custom FastAPI/ONNX server (CPU), scale-to-zero, venv-on-PVC.

**Non-text domain model**: base64 image input — does **not** expose OpenAI `/v1/embeddings`.
Serves `POST /v1/science/embed` (with `/v1/vision/embed` as a secondary alias).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + ONNX weights (nfs-models, already RWX)
kubectl apply -f inferenceservice.yaml # ConfigMap (server.py) + ISVC, CPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/dino-vit-b8/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **6 PASS / 0 FAIL** — dim 768, non-zero, distinctness, deterministic,
model-echo, malformed. (Test generates a pure-stdlib PNG — no PIL needed in the gateway pod.)

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + ONNX Runtime (CPUExecutionProvider) |
| Endpoint | `POST /v1/science/embed` (domain; base64 image; `/v1/vision/embed` secondary) |
| Embedding dim | 768 (ViT-B/8 CLS) |
| Input | `image` base64 PNG/JPEG (resized 224×224, ImageNet-normalized) |
| Parameters | 86M |
| GPU | none (CPU, ONNX) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| PVC | `dino-vit-b8-data` (RWX, nfs-models) — venv + ONNX weights |
