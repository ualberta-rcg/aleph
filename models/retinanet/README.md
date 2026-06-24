# retinanet

RetinaNet ResNet-50 FPN v2 object detector served as a KServe custom predictor.

- Model id: `retinanet-resnet50`
- Endpoint: `POST /v1/vision/detect`
- Runtime: PyTorch (`torchvision.models.detection.retinanet_resnet50_fpn_v2`)

## HF / upstream I/O reference

- Upstream page: <https://pytorch.org/vision/stable/models/retinanet.html>
- Task: dense object detection with COCO classes.
- Input: RGB image tensor.
- Output: bounding boxes, class labels, confidence scores.

## Gateway request

```json
{
  "model": "retinanet-resnet50",
  "image": "<base64-png-or-jpg>"
}
```

## Gateway response

```json
{
  "model": "retinanet-resnet50",
  "task": "detect",
  "detections": [{"label":"bus","score":0.95,"box":[x1,y1,x2,y2]}]
}
```
