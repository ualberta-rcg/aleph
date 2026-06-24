# efficientnet-b0

EfficientNet-Lite4 image classifier served via ONNX Runtime on CPU.

- Model id: `efficientnet-b0`
- Endpoint: `POST /v1/vision/classify`
- Runtime: ONNX (`onnx/EfficientNet-Lite4`)

## HF / upstream I/O reference

- Upstream repo: <https://huggingface.co/onnx/EfficientNet-Lite4>
- ONNX model-zoo format: image classification (ImageNet-1k).
- Input: one RGB image, preprocessed by resize/crop and normalized to Lite4 expected range.
- Output: class probabilities/logits mapped to ImageNet labels.

## Gateway request

```json
{
  "model": "efficientnet-b0",
  "image": "<base64-png-or-jpg>",
  "top_k": 5
}
```

## Gateway response

```json
{
  "model": "efficientnet-b0",
  "task": "classify",
  "predictions": [{"rank":1,"class_id":817,"label":"sports car","score":0.61}]
}
```
