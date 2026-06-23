# arcface Notes

## Purpose
ArcFace ResNet-100 (DeepInsight) face recognition. 512-dim L2-normalized embeddings
for face verification/identification via `/v1/vision/face` (base64 image in).

## Runtime
- Custom FastAPI + onnxruntime (CPU), venv-on-PVC. ONNX model from
  `onnx-community/arcface-onnx` (`arcface.onnx`). No HF token needed (public).
- Pinned `onnxruntime==1.19.2`.

## Migration changes vs 232
- Already Knative+PVC+init; only pinned onnxruntime, converted card to v2,
  added `routing.k8s_name: arcface`.

## Resources
- CPU req/limit 1/2; mem 1Gi/2Gi. PVC `arcface-data` 5Gi (RWX, nfs-models).

## Quirks
- Input preprocessing: resize 112x112, RGB->BGR, (x-127.5)/128.0, NHWC.
- Output already L2-normalized; compare with cosine similarity.

## Validation
See [TEST.md](TEST.md). dim=512, normalized.
