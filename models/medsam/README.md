# MedSAM

Medical image segmentation based on Meta's Segment Anything Model (SAM), fine-tuned on medical imaging data.

| Field | Value |
|---|---|
| ID | `medsam` |
| Endpoint | `POST /v1/science/segment` |
| Source | [flaviagiammarino/medsam-vit-base](https://huggingface.co/flaviagiammarino/medsam-vit-base) |
| License | Apache-2.0 |
| Parameters | ~375M |
| GPU | Yes (L40S shared) |

## Input

```json
{
  "image": [[[R,G,B], ...], ...],
  "boxes": [[x_min, y_min, x_max, y_max], ...]
}
```

- `image`: HxW array of RGB pixel values (0-255)
- `boxes`: bounding box prompt(s); defaults to full image if omitted

## Output

```json
{
  "masks": [[...bool...]],
  "scores": [0.95, ...],
  "model": "medsam",
  "image_size": [H, W]
}
```
