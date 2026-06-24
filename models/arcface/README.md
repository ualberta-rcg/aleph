# arcface

ArcFace ResNet-100 face recognition model served as a KServe custom predictor.

- Model id: `arcface-resnet100`
- Endpoint: `POST /v1/vision/face`
- Runtime: ONNX Runtime (CPU)

## Upstream reference

- Source: <https://huggingface.co/onnx-community/arcface-onnx>
- Task: Face recognition / verification via 512-dim embeddings.
- Input: RGB face image (resized to 112x112, BGR-normalized).
- Output: 512-dim L2-normalized embedding. Compare faces via cosine similarity.

## Gateway request

```json
{
  "model": "arcface-resnet100",
  "image": "<base64-png-or-jpg>"
}
```

## Gateway response

```json
{
  "model": "arcface-resnet100",
  "task": "face",
  "embedding": [0.012, -0.034, ...],
  "dim": 512
}
```
