# TotalSegmentator

Automated CT scan segmentation of 117 anatomical structures using nnU-Net.

| Field | Value |
|---|---|
| ID | `totalsegmentator` |
| Endpoint | `POST /v1/science/segment` |
| Source | [wasserth/TotalSegmentator](https://github.com/wasserth/TotalSegmentator) |
| License | Apache-2.0 |
| Parameters | ~31M |
| GPU | Yes (L40S shared) |

## Input

```json
{
  "ct_array": [[[...], ...], ...],
  "spacing": [1.5, 1.5, 1.5],
  "fast": true,
  "task": "total"
}
```

- `ct_array`: 3D array [D, H, W] of Hounsfield Unit values (int16)
- `spacing`: voxel spacing in mm [z, y, x] (default: [1.5, 1.5, 1.5])
- `fast`: use fast mode (default: true)
- `task`: segmentation task (default: "total")

## Output

```json
{
  "model": "totalsegmentator",
  "segmentation": [[[...]]],
  "segmentation_shape": [D, H, W],
  "num_structures": 117
}
```
