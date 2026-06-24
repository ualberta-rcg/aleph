# maskrcnn

Mask R-CNN ResNet-50 FPN v2 instance segmentation model served as a KServe custom predictor.

- Model id: `maskrcnn-resnet50`
- Endpoint: `POST /v1/vision/segment`
- Runtime: PyTorch (`torchvision.models.detection.maskrcnn_resnet50_fpn_v2`)

## HF / upstream I/O reference

- Upstream page: <https://pytorch.org/vision/stable/models/mask_rcnn.html>
- Task: instance segmentation with COCO classes.
- Input: RGB image tensor.
- Output: detections with class labels, confidence scores, and bounding boxes (masks are available in the base model but this server returns detection boxes + labels/scores).

## Gateway request

```json
{
  "model": "maskrcnn-resnet50",
  "image": "<base64-png-or-jpg>"
}
```

## Gateway response

```json
{
  "model": "maskrcnn-resnet50",
  "task": "segment",
  "detections": [{"label":"person","score":0.99,"box":[x1,y1,x2,y2]}]
}
```
